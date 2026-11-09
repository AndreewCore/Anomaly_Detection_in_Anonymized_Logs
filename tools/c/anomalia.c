#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>
#include <time.h>
#include <pthread.h>
#include <sys/resource.h>

// Valores por defecto del modo ssh cuando no se pasan opciones. Mantienen el
// comportamiento histórico (un diccionario corto) para quien ejecute sin flags.
#define DEF_INTENTOS   1      // claves probadas por usuario (-n)
#define DEF_PAUSA_MS   2000   // pausa entre intentos en ms (-p)
#define DURACION_CPU   30
#define DURACION_RAM   20
#define PCT_RAM        0.80

// Diccionario por defecto. El laboratorio normalmente lo sobrescribe con -u/-w
// desde el escenario, pero sin flags reproduce un ataque mínimo reconocible.
static const char *usuarios_def[] = {"admin", "root", "test", "guest", "user1", "administrator"};
static const char *claves_def[]   = {"123456", "password", "admin123", "qwerty", "letmein", "12345678"};
#define NUM_DEF 6

// Config del modo ssh, poblada desde argv para no depender de #define fijos.
typedef struct {
    const char *host;
    const char **usuarios; int n_usuarios;
    const char **claves;   int n_claves;
    int intentos;          // claves por usuario y ráfaga
    long pausa_ms;
    int duracion_s;        // ventana del segmento; 0 = una sola ráfaga sin espera
    int rafagas;
    unsigned seed;
    const char *gt_path;   // CSV de Ground Truth (append); NULL = no escribir
    const char *src_ip;    // IP propia, para la fila de GT
    const char *atacante;  // nombre lógico (p. ej. attacker_1), para la fila de GT
    const char *escenario;
    int segmento;
} ssh_cfg;

// Marca de tiempo UTC ISO-8601 con milisegundos (2026-11-09T14:03:01.123Z).
// El GT se alinea por tiempo contra el auth.log, así que la precisión importa.
static void iso_utc_ms(char *buf, size_t n)
{
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    struct tm tm;
    gmtime_r(&ts.tv_sec, &tm);
    size_t len = strftime(buf, n, "%Y-%m-%dT%H:%M:%S", &tm);
    snprintf(buf + len, n - len, ".%03ldZ", ts.tv_nsec / 1000000);
}

// Lanza un intento de login SSH con credenciales inválidas para que sshd lo
// rechace y lo registre. Espera a que el hijo termine (ataque secuencial).
static void intento_ssh(const char *host, const char *usuario, const char *clave)
{
    char destino[256];
    snprintf(destino, sizeof(destino), "%s@%s", usuario, host);
    pid_t pid = fork();
    if (pid == 0)
    {
        char *args[] = {
            "sshpass", "-p", (char *)clave,
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=3",
            "-o", "NumberOfPasswordPrompts=1",
            destino,
            NULL
        };
        freopen("/dev/null", "w", stdout);
        freopen("/dev/null", "w", stderr);
        execvp(args[0], args);
        _exit(1);
    }
    else if (pid > 0)
    {
        waitpid(pid, NULL, 0);
    }
}

// Intento fallido de FTP contra <host> (antes ignoraba el host y pegaba siempre
// a localhost; ver docs/pendientes.md).
static void intento_ftp(const char *host, const char *usuario, const char *clave)
{
    pid_t pid = fork();
    if (pid == 0)
    {
        char credencial[128];
        char url[256];
        snprintf(credencial, sizeof(credencial), "%s:%s", usuario, clave);
        snprintf(url, sizeof(url), "ftp://%s/", host);
        char *args[] = {
            "curl",
            "-u", credencial,
            "--connect-timeout", "3",
            "-s", "-o", "/dev/null",
            url,
            NULL
        };
        freopen("/dev/null", "w", stdout);
        freopen("/dev/null", "w", stderr);
        execvp(args[0], args);
        _exit(1);
    }
    else if (pid > 0)
    {
        waitpid(pid, NULL, 0);
    }
}

// Segundos transcurridos desde un instante de referencia (monotónico, inmune a
// ajustes del reloj de pared durante la captura).
static double transcurrido(const struct timespec *inicio)
{
    struct timespec ahora;
    clock_gettime(CLOCK_MONOTONIC, &ahora);
    return (ahora.tv_sec - inicio->tv_sec) + (ahora.tv_nsec - inicio->tv_nsec) / 1e9;
}

// Ejecuta una ráfaga: cada usuario recibe `intentos` claves. Registra una fila
// de GT por intento, con un intervalo [inicio, fin] ajustado a ese intento para
// que el parser lo asocie al evento correcto del auth.log.
static void ejecutar_rafaga(const ssh_cfg *c, int burst_id, FILE *gt)
{
    for (int u = 0; u < c->n_usuarios; u++)
    {
        for (int k = 0; k < c->intentos; k++)
        {
            const char *clave = c->claves[(u + k) % c->n_claves];
            char ini[40], fin[40];
            iso_utc_ms(ini, sizeof(ini));
            intento_ssh(c->host, c->usuarios[u], clave);
            iso_utc_ms(fin, sizeof(fin));
            if (gt)
            {
                // Columnas: scenario,segment,burst_id,attacker,src_ip,user,ts_start,ts_end
                fprintf(gt, "%s,%d,%d,%s,%s,%s,%s,%s\n",
                        c->escenario ? c->escenario : "",
                        c->segmento, burst_id,
                        c->atacante ? c->atacante : "",
                        c->src_ip ? c->src_ip : "",
                        c->usuarios[u], ini, fin);
                fflush(gt);
            }
            if (c->pausa_ms > 0)
                usleep((useconds_t)(c->pausa_ms * 1000));
        }
    }
}

// Reparte `rafagas` a lo largo de `duracion_s`, con un desfase seudoaleatorio por
// ráfaga (semilla -s). Así la partición temporal train/test deja ataques en ambos
// lados (decisión D4) y dos corridas con la misma semilla son reproducibles.
static void ejecutar_ssh(const ssh_cfg *c)
{
    FILE *gt = NULL;
    if (c->gt_path)
    {
        gt = fopen(c->gt_path, "a");
        if (!gt) { perror("no se pudo abrir el CSV de Ground Truth"); }
    }

    printf("ataque ssh contra %s — %d usuario(s) x %d clave(s), %d rafaga(s)\n",
           c->host, c->n_usuarios, c->intentos, c->rafagas);

    if (c->rafagas <= 1 || c->duracion_s <= 0)
    {
        // Sin ventana temporal: una sola ráfaga inmediata (modo rápido/pruebas).
        ejecutar_rafaga(c, 0, gt);
    }
    else
    {
        struct timespec inicio;
        clock_gettime(CLOCK_MONOTONIC, &inicio);
        srand(c->seed);
        double paso = (double)c->duracion_s / c->rafagas;
        for (int b = 0; b < c->rafagas; b++)
        {
            // Objetivo: centro de la franja b, con jitter dentro de ±40% del paso.
            double jitter = ((double)rand() / RAND_MAX - 0.5) * 0.8 * paso;
            double objetivo = paso * b + paso * 0.5 + jitter;
            if (objetivo < 0) objetivo = 0;
            double espera = objetivo - transcurrido(&inicio);
            if (espera > 0) sleep((unsigned)espera);
            printf("  rafaga %d/%d a los %.0f s\n", b + 1, c->rafagas, transcurrido(&inicio));
            ejecutar_rafaga(c, b, gt);
        }
    }

    if (gt) fclose(gt);
    printf("ataque ssh terminado\n");
}

// Convierte "a,b,c" en un arreglo de punteros dentro del mismo buffer (lo muta
// reemplazando las comas por '\0'). Devuelve cuántos elementos quedaron.
static int split_csv(char *s, const char **out, int max)
{
    int n = 0;
    char *tok = strtok(s, ",");
    while (tok && n < max)
    {
        out[n++] = tok;
        tok = strtok(NULL, ",");
    }
    return n;
}

// estres de CPU / RAM — heredados de SIEMLite, fuera del alcance del experimento.

volatile int cpu_activo = 1;

static void *hilo_cpu(void *arg)
{
    (void)arg;
    // Baja la prioridad para no bloquear al resto del sistema; el tiempo de CPU
    // se sigue contando en /proc/stat, así que la señal de carga no se pierde.
    setpriority(PRIO_PROCESS, 0, 19);
    volatile double x = 1.0;
    while (cpu_activo)
        x = x * 1.0000001 + 0.0000001;
    return NULL;
}

static void estresar_cpu(void)
{
    int nucleos = (int)sysconf(_SC_NPROCESSORS_ONLN);
    if (nucleos < 1) nucleos = 1;
    pthread_t hilos[64];
    int lanzados = nucleos < 64 ? nucleos : 64;
    printf("estresando CPU con %d hilos durante %d segundos...\n", lanzados, DURACION_CPU);
    for (int i = 0; i < lanzados; i++)
        pthread_create(&hilos[i], NULL, hilo_cpu, NULL);
    sleep(DURACION_CPU);
    cpu_activo = 0;
    for (int i = 0; i < lanzados; i++)
        pthread_join(hilos[i], NULL);
}

static long leer_ram_total(void)
{
    FILE *f = fopen("/proc/meminfo", "r");
    if (!f) return 0;
    char linea[128];
    long total_kb = 0;
    while (fgets(linea, sizeof(linea), f))
    {
        if (strncmp(linea, "MemTotal:", 9) == 0)
        {
            sscanf(linea, "MemTotal: %ld kB", &total_kb);
            break;
        }
    }
    fclose(f);
    return total_kb * 1024;
}

static void estresar_ram(void)
{
    long total = leer_ram_total();
    if (total <= 0) { printf("no se pudo leer la RAM del sistema\n"); return; }
    long bytes = (long)(total * PCT_RAM);
    printf("consumiendo %.0f%% de RAM (%ld MB) durante %d segundos...\n",
           PCT_RAM * 100, bytes / 1024 / 1024, DURACION_RAM);
    char *bloque = malloc(bytes);
    if (!bloque) { printf("malloc fallo — puede que no haya suficiente RAM libre\n"); return; }
    memset(bloque, 0xAB, bytes);
    sleep(DURACION_RAM);
    free(bloque);
}

// main

static void uso(const char *prog)
{
    printf("uso: %s <modo> [host] [opciones]\n\n", prog);
    printf("  ssh <host> [opciones]   ataque de fuerza bruta SSH contra <host>\n");
    printf("  ftp <host>              intentos fallidos de login FTP contra <host>\n");
    printf("  cpu                     estresa los nucleos (heredado, fuera del experimento)\n");
    printf("  ram                     consume RAM (heredado, fuera del experimento)\n\n");
    printf("opciones del modo ssh:\n");
    printf("  -u a,b,c   usuarios objetivo (coma)        [def: diccionario interno]\n");
    printf("  -w a,b,c   claves a probar (coma)          [def: diccionario interno]\n");
    printf("  -n N       claves por usuario y rafaga     [def: %d]\n", DEF_INTENTOS);
    printf("  -p MS      pausa entre intentos en ms      [def: %d]\n", DEF_PAUSA_MS);
    printf("  -d SEG     duracion del segmento en s      [def: 0 = una rafaga]\n");
    printf("  -b N       numero de rafagas en el segmento[def: 1]\n");
    printf("  -s SEED    semilla del desfase de rafagas  [def: 0]\n");
    printf("  -g FILE    CSV de Ground Truth (append)\n");
    printf("  -I IP      IP de origen propia (para el GT)\n");
    printf("  -a NAME    nombre del atacante (para el GT)\n");
    printf("  -S NAME    escenario (para el GT)\n");
    printf("  -k N       segmento (para el GT)\n");
}

int main(int argc, char *argv[])
{
    if (argc < 2) { uso(argv[0]); return 1; }
    char *modo = argv[1];

    if (strcmp(modo, "ssh") == 0)
    {
        if (argc < 3 || argv[2][0] == '-')
        {
            printf("falta el host\nuso: %s ssh <host> [opciones]\n", argv[0]);
            return 1;
        }
        // Buffers mutables para -u/-w: split_csv escribe '\0' sobre las comas.
        const char *users_buf[256], *pass_buf[256];
        char *u_arg = NULL, *w_arg = NULL;
        ssh_cfg c = {0};
        c.host = argv[2];
        c.intentos = DEF_INTENTOS;
        c.pausa_ms = DEF_PAUSA_MS;
        c.rafagas = 1;

        // getopt empieza tras "ssh <host>"; saltamos esos dos primeros argumentos.
        int opt;
        optind = 3;
        while ((opt = getopt(argc, argv, "u:w:n:p:d:b:s:g:I:a:S:k:")) != -1)
        {
            switch (opt)
            {
                case 'u': u_arg = optarg; break;
                case 'w': w_arg = optarg; break;
                case 'n': c.intentos = atoi(optarg); break;
                case 'p': c.pausa_ms = atol(optarg); break;
                case 'd': c.duracion_s = atoi(optarg); break;
                case 'b': c.rafagas = atoi(optarg); break;
                case 's': c.seed = (unsigned)strtoul(optarg, NULL, 10); break;
                case 'g': c.gt_path = optarg; break;
                case 'I': c.src_ip = optarg; break;
                case 'a': c.atacante = optarg; break;
                case 'S': c.escenario = optarg; break;
                case 'k': c.segmento = atoi(optarg); break;
                default: uso(argv[0]); return 1;
            }
        }

        if (u_arg) c.n_usuarios = split_csv(u_arg, users_buf, 256);
        else { for (int i = 0; i < NUM_DEF; i++) users_buf[i] = usuarios_def[i]; c.n_usuarios = NUM_DEF; }
        if (w_arg) c.n_claves = split_csv(w_arg, pass_buf, 256);
        else { for (int i = 0; i < NUM_DEF; i++) pass_buf[i] = claves_def[i]; c.n_claves = NUM_DEF; }
        c.usuarios = users_buf;
        c.claves = pass_buf;
        if (c.intentos < 1) c.intentos = 1;

        ejecutar_ssh(&c);
    }
    else if (strcmp(modo, "ftp") == 0)
    {
        if (argc < 3) { printf("falta el host\nuso: %s ftp <host>\n", argv[0]); return 1; }
        for (int i = 0; i < NUM_DEF; i++)
        {
            const char *usuario = usuarios_def[i % NUM_DEF];
            const char *clave   = claves_def[i % NUM_DEF];
            intento_ftp(argv[2], usuario, clave);
            sleep(2);
        }
        printf("ataque ftp terminado\n");
    }
    else if (strcmp(modo, "cpu") == 0) { estresar_cpu(); printf("estres de CPU terminado\n"); }
    else if (strcmp(modo, "ram") == 0) { estresar_ram(); printf("estres de RAM terminado\n"); }
    else
    {
        printf("modo desconocido: %s\n\n", modo);
        uso(argv[0]);
        return 1;
    }
    return 0;
}

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <errno.h>
#include <time.h>
#include <sys/statvfs.h>   // para leer uso de disco
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#define MAXS          10
#define MAXLOG        8
#define MAX_MSG       1024
#define PUERTO_DEFAULT 9000

// Variables globales necesarias para cerrar todo limpiamente desde el manejador de senal
static pid_t pids_hijos[MAXS];
static int   num_serv_g = 0;
static int   sock_srv   = -1;

// Buffer circular de los ultimos logs recibidos
static char logs_recientes[MAXLOG][256];
static int  log_pos = 0;

// Valores anteriores de CPU para calcular el porcentaje por diferencial
static long cpu_prev_total = 0;
static long cpu_prev_idle  = 0;

// Al presionar Ctrl+C se terminan los journalctl y se cierra el socket
static void sig_handler(int sig)
{
    (void)sig;
    for (int i = 0; i < num_serv_g; i++)
        kill(pids_hijos[i], SIGTERM);
    if (sock_srv >= 0)
        close(sock_srv);
    printf("\n[agente] cerrando...\n");
    exit(0);
}

// Extrae el valor de un campo del JSON que genera journalctl
static void get_campo(const char *linea, const char *campo, char *dst, int max)
{
    char buscar[64];
    snprintf(buscar, sizeof(buscar), "\"%s\":\"", campo);
    const char *ini = strstr(linea, buscar);
    if (!ini) { dst[0] = '\0'; return; }
    ini += strlen(buscar);
    const char *fin = strchr(ini, '"');
    if (!fin) { dst[0] = '\0'; return; }
    int len = (int)(fin - ini);
    if (len >= max) len = max - 1;
    strncpy(dst, ini, len);
    dst[len] = '\0';
}

// Guarda el log en el buffer circular sobreescribiendo el mas antiguo
static void add_log(const char *serv, int prio, const char *msg)
{
    snprintf(logs_recientes[log_pos], 256, "[%d][%s] %.180s", prio, serv, msg);
    log_pos = (log_pos + 1) % MAXLOG;
}

// Lee /proc/stat dos veces y calcula el porcentaje de CPU usado en ese periodo
static double leer_cpu_pct(void)
{
    FILE *f = fopen("/proc/stat", "r");
    if (!f) return 0.0;

    long user, nice, system, idle, iowait, irq, softirq;
    fscanf(f, "cpu  %ld %ld %ld %ld %ld %ld %ld",
           &user, &nice, &system, &idle, &iowait, &irq, &softirq);
    fclose(f);

    long total      = user + nice + system + idle + iowait + irq + softirq;
    long idle_total = idle + iowait;

    // El porcentaje se calcula como la fraccion de tiempo que no estuvo inactivo
    long delta_total = total - cpu_prev_total;
    long delta_idle  = idle_total - cpu_prev_idle;

    cpu_prev_total = total;
    cpu_prev_idle  = idle_total;

    if (delta_total <= 0) return 0.0;
    return (1.0 - (double)delta_idle / (double)delta_total) * 100.0;
}

// Lee /proc/meminfo y calcula el porcentaje de RAM utilizada
static double leer_ram_pct(void)
{
    FILE *f = fopen("/proc/meminfo", "r");
    if (!f) return 0.0;

    long mem_total = 0, mem_available = 0;
    char linea[128];

    // MemAvailable es lo que realmente pueden usar los procesos, mas preciso que MemFree
    while (fgets(linea, sizeof(linea), f)) {
        if (strncmp(linea, "MemTotal:", 9) == 0)
            sscanf(linea + 9, "%ld", &mem_total);
        else if (strncmp(linea, "MemAvailable:", 13) == 0)
            sscanf(linea + 13, "%ld", &mem_available);
        if (mem_total > 0 && mem_available > 0) break;
    }
    fclose(f);

    if (mem_total <= 0) return 0.0;
    return (1.0 - (double)mem_available / (double)mem_total) * 100.0;
}

// Usa statvfs para calcular el porcentaje de disco usado en la particion raiz
static double leer_disco_pct(void)
{
    struct statvfs st;
    if (statvfs("/", &st) != 0) return 0.0;
    if (st.f_blocks == 0) return 0.0;
    // f_bavail son los bloques disponibles para usuarios normales
    return (1.0 - (double)st.f_bavail / (double)st.f_blocks) * 100.0;
}

// Establece la conexion TCP con el servidor y retorna el fd del socket
static int conectar_servidor(const char *host, int puerto)
{
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) { perror("[agente] socket"); return -1; }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port   = htons(puerto);

    // inet_pton convierte la IP en texto a formato binario que usa el socket
    if (inet_pton(AF_INET, host, &addr.sin_addr) <= 0) {
        fprintf(stderr, "[agente] IP invalida: %s\n", host);
        close(fd);
        return -1;
    }

    if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        fprintf(stderr, "[agente] No se pudo conectar a %s:%d — %s\n",
                host, puerto, strerror(errno));
        close(fd);
        return -1;
    }

    printf("[agente] Conectado al servidor %s:%d\n", host, puerto);
    return fd;
}

// Envia una linea JSON al servidor terminada en '\n' que es el delimitador del protocolo
static void enviar_al_servidor(const char *json)
{
    if (sock_srv < 0) return;

    char buf[MAX_MSG + 2];
    int len = snprintf(buf, sizeof(buf), "%s\n", json);

    if (send(sock_srv, buf, len, 0) < 0) {
        fprintf(stderr, "[agente] Conexion perdida: %s\n", strerror(errno));
        close(sock_srv);
        sock_srv = -1; // se reintentara en el proximo intervalo
    }
}

static void enviar_identificacion(const char *nombre)
{
    char json[256];
    snprintf(json, sizeof(json), "{\"tipo\":\"identificacion\",\"agente\":\"%s\"}", nombre);
    enviar_al_servidor(json);
}

static void enviar_metricas(const char *nombre, double cpu, double ram, double disco)
{
    char json[256];
    snprintf(json, sizeof(json),
        "{\"tipo\":\"metrica\",\"agente\":\"%s\","
        "\"cpu\":%.1f,\"ram_pct\":%.1f,\"disco_pct\":%.1f}",
        nombre, cpu, ram, disco);
    enviar_al_servidor(json);
}

static void enviar_log(const char *nombre, const char *servicio, int prio, const char *mensaje)
{
    // Escapar comillas dobles para no romper el JSON
    char msg_safe[512];
    int j = 0;
    for (int i = 0; mensaje[i] && j < 500; i++) {
        if (mensaje[i] == '"' || mensaje[i] == '\\') msg_safe[j++] = '\\';
        msg_safe[j++] = mensaje[i];
    }
    msg_safe[j] = '\0';

    char json[MAX_MSG];
    snprintf(json, sizeof(json),
        "{\"tipo\":\"log\",\"agente\":\"%s\","
        "\"servicio\":\"%s\",\"prioridad\":%d,\"mensaje\":\"%s\"}",
        nombre, servicio, prio, msg_safe);
    enviar_al_servidor(json);
}

// Muestra el estado del agente en su propia terminal
static void mostrar_estado_local(const char *nombre, double cpu,
                                  double ram, double disco,
                                  const char *host, int conectado)
{
    printf("\033[H\033[J");
    time_t ahora = time(NULL);
    char tbuf[32];
    strftime(tbuf, sizeof(tbuf), "%H:%M:%S", localtime(&ahora));

    printf("── Agente SIEMLite: %-10s  %s ──\n", nombre, tbuf);
    if (conectado)
        printf("Servidor: %-15s  [\033[1;32mCONECTADO\033[0m]\n\n", host);
    else
        printf("Servidor: %-15s  [\033[1;31mDESCONECTADO — reintentando...\033[0m]\n\n", host);

    printf("  CPU: %5.1f%%   RAM: %5.1f%%   Disco: %5.1f%%\n\n", cpu, ram, disco);

    printf("Ultimos logs:\n");
    for (int i = 0; i < MAXLOG; i++) {
        int idx = (log_pos + i) % MAXLOG;
        if (logs_recientes[idx][0])
            printf("  %s\n", logs_recientes[idx]);
    }
    fflush(stdout);
}

int main(int argc, char *argv[])
{
    setvbuf(stdout, NULL, _IONBF, 0);

    char *serv[MAXS];
    int   num_serv  = 0;
    int   intervalo = 0;
    char  nombre_agente[64] = "agente";
    char  host_srv[128]     = "127.0.0.1";
    int   puerto_srv        = PUERTO_DEFAULT;

    int opt;
    while ((opt = getopt(argc, argv, "s:t:a:H:P:")) != -1) {
        switch (opt) {
        case 's': if (num_serv < MAXS) serv[num_serv++] = strdup(optarg); break;
        case 't': intervalo = atoi(optarg); break;
        case 'a': strncpy(nombre_agente, optarg, sizeof(nombre_agente) - 1); break;
        case 'H': strncpy(host_srv, optarg, sizeof(host_srv) - 1); break;
        case 'P': puerto_srv = atoi(optarg); break;
        default:
            fprintf(stderr,
                "Uso: %s -a <nombre> -s <servicio> [-s ...] -t <seg> -H <ip_servidor>\n",
                argv[0]);
            return 1;
        }
    }

    if (num_serv < 1) { fprintf(stderr, "Se necesita al menos un -s\n"); return 1; }
    if (intervalo <= 0) { fprintf(stderr, "-t debe ser mayor a 0\n"); return 1; }

    num_serv_g = num_serv;
    signal(SIGINT,  sig_handler);
    signal(SIGCHLD, SIG_IGN);

    // Conectar al servidor al inicio; si falla el agente igual arranca y reintenta
    sock_srv = conectar_servidor(host_srv, puerto_srv);
    if (sock_srv >= 0)
        enviar_identificacion(nombre_agente);
    else
        printf("[agente] Sin servidor — reintentando cada %d s\n", intervalo);

    // Lanzar un proceso journalctl por cada servicio usando fork + pipe + exec
    int  pipes[MAXS][2];
    FILE *lectores[MAXS];

    for (int i = 0; i < num_serv; i++) {
        if (pipe(pipes[i]) < 0) { perror("pipe"); return 1; }

        pid_t pid = fork();
        if (pid < 0) { perror("fork"); return 1; }

        if (pid == 0) {
            // El hijo redirige su stdout al extremo de escritura del pipe
            close(pipes[i][0]);
            dup2(pipes[i][1], STDOUT_FILENO);
            close(pipes[i][1]);

            // journalctl -f mantiene el proceso corriendo y entrega logs en tiempo real
            char *args[] = { "journalctl", "-u", serv[i], "-o", "json", "-f", NULL };
            execvp(args[0], args);
            _exit(1);
        }

        // El padre guarda el extremo de lectura para leerlo con select
        close(pipes[i][1]);
        pids_hijos[i] = pid;
        lectores[i]   = fdopen(pipes[i][0], "r");
    }

    // Primera lectura de /proc/stat para establecer el baseline del calculo de CPU
    leer_cpu_pct();

    time_t ultima_act = time(NULL);

    while (1) {
        // Vigilar todos los pipes con select para no bloquear en ninguno
        fd_set fds;
        FD_ZERO(&fds);
        int maxfd = 0;
        for (int i = 0; i < num_serv; i++) {
            FD_SET(pipes[i][0], &fds);
            if (pipes[i][0] > maxfd) maxfd = pipes[i][0];
        }

        struct timeval tv = {1, 0};
        int listos = select(maxfd + 1, &fds, NULL, NULL, &tv);

        if (listos > 0) {
            for (int i = 0; i < num_serv; i++) {
                if (!FD_ISSET(pipes[i][0], &fds)) continue;

                char linea[4096];
                if (!fgets(linea, sizeof(linea), lectores[i])) continue;

                char prio_txt[8] = "7", msg[512] = "";
                get_campo(linea, "PRIORITY", prio_txt, sizeof(prio_txt));
                get_campo(linea, "MESSAGE",  msg,      sizeof(msg));

                int prio = atoi(prio_txt);
                if (prio < 0 || prio > 7) prio = 7;

                add_log(serv[i], prio, msg);
                enviar_log(nombre_agente, serv[i], prio, msg);
            }
        }

        time_t ahora = time(NULL);
        if (ahora - ultima_act >= intervalo) {
            ultima_act = ahora;

            // Si se perdio la conexion con el servidor intentar reconectar
            if (sock_srv < 0) {
                sock_srv = conectar_servidor(host_srv, puerto_srv);
                if (sock_srv >= 0) enviar_identificacion(nombre_agente);
            }

            double cpu   = leer_cpu_pct();
            double ram   = leer_ram_pct();
            double disco = leer_disco_pct();

            enviar_metricas(nombre_agente, cpu, ram, disco);
            mostrar_estado_local(nombre_agente, cpu, ram, disco, host_srv, sock_srv >= 0);
        }
    }

    return 0;
}

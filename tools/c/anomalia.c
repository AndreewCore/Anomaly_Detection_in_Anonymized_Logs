#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>
#include <time.h>
#include <pthread.h>
#include <sys/resource.h>

// numero de intentos fallidos de autenticacion que se generan
#define INTENTOS     6
// pausa en segundos entre cada intento de autenticacion
#define PAUSA        2
// duracion en segundos del estres de CPU o RAM
#define DURACION_CPU 30
#define DURACION_RAM 20
// porcentaje de RAM del sistema que se va a consumir para la prueba
#define PCT_RAM      0.80

// lista de usuarios y claves comunes para simular un diccionario de fuerza bruta real
static const char *usuarios[] = {"admin", "root", "test", "guest", "user1", "administrator"};
static const char *claves[]   = {"123456", "password", "admin123", "qwerty", "letmein", "12345678"};
#define NUM_CREDENCIALES 6

// intentos fallidos de SSH

// lanza un intento de login SSH con credenciales invalidas para que sshd lo rechace y lo loguee
void intento_ssh(const char *usuario, const char *clave)
{
    pid_t pid = fork();
    if (pid == 0)
    {
        char *args[] = {
            "sshpass", "-p", (char *)clave,
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=3",
            "-o", "NumberOfPasswordPrompts=1",
            (char *)usuario,
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

// intentos fallidos de FTP (vsftpd)

// conecta al servicio FTP local con usuario y clave incorrectos para generar entradas en el log de vsftpd
void intento_ftp(const char *usuario, const char *clave)
{
    pid_t pid = fork();
    if (pid == 0)
    {
        char credencial[128];
        snprintf(credencial, sizeof(credencial), "%s:%s", usuario, clave);
        char *args[] = {
            "curl",
            "-u", credencial,
            "--connect-timeout", "3",
            "-s", "-o", "/dev/null",
            "ftp://localhost/",
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

// estres de CPU

// bandera para detener los hilos de CPU cuando expire el tiempo
volatile int cpu_activo = 1;

// cada hilo ejecuta un bucle infinito de operaciones para saturar un nucleo
void *hilo_cpu(void *arg)
{
    (void)arg;
    // baja la prioridad de este hilo para que el kernel no bloquee al resto del sistema
    // el tiempo de CPU usado se sigue contando igual en /proc/stat, la alerta no se ve afectada
    setpriority(PRIO_PROCESS, 0, 19);
    volatile double x = 1.0;
    while (cpu_activo)
        x = x * 1.0000001 + 0.0000001;
    return NULL;
}

// lanza tantos hilos como nucleos tenga el sistema para maximizar el uso de CPU
void estresar_cpu(void)
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

// estres de RAM

// lee /proc/meminfo y devuelve la RAM total del sistema en bytes
long leer_ram_total(void)
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

// reserva un porcentaje de la RAM total y la mantiene ocupada para que el agente detecte uso alto
void estresar_ram(void)
{
    long total = leer_ram_total();
    if (total <= 0)
    {
        printf("no se pudo leer la RAM del sistema\n");
        return;
    }

    long bytes = (long)(total * PCT_RAM);
    printf("consumiendo %.0f%% de RAM (%ld MB) durante %d segundos...\n",
           PCT_RAM * 100, bytes / 1024 / 1024, DURACION_RAM);

    // reserva el bloque y lo escribe para que el SO realmente lo asigne en fisico
    char *bloque = malloc(bytes);
    if (!bloque)
    {
        printf("malloc fallo — puede que no haya suficiente RAM libre\n");
        return;
    }
    memset(bloque, 0xAB, bytes);

    sleep(DURACION_RAM);
    free(bloque);
}

// main

void uso(const char *prog)
{
    printf("uso: %s <modo> [host]\n\n", prog);
    printf("  ssh <host>   genera %d intentos fallidos de login SSH contra <host>\n", INTENTOS);
    printf("  ftp <host>   genera %d intentos fallidos de login FTP contra <host>\n", INTENTOS);
    printf("  cpu          estresa todos los nucleos durante %d segundos\n", DURACION_CPU);
    printf("  ram          consume el %.0f%% de la RAM durante %d segundos\n",
           PCT_RAM * 100, DURACION_RAM);
}

int main(int argc, char *argv[])
{
    if (argc < 2) { uso(argv[0]); return 1; }

    char *modo = argv[1];

    // modo SSH — recorre una lista de usuarios y claves comunes, como un diccionario real
    if (strcmp(modo, "ssh") == 0)
    {
        if (argc < 3) { printf("falta el host\nuso: %s ssh <host>\n", argv[0]); return 1; }
        printf("simulando ataque de fuerza bruta SSH contra %s — %d intentos\n", argv[2], INTENTOS);
        for (int i = 0; i < INTENTOS; i++)
        {
            const char *usuario = usuarios[i % NUM_CREDENCIALES];
            const char *clave   = claves[i % NUM_CREDENCIALES];
            char destino[128];
            snprintf(destino, sizeof(destino), "%s@%s", usuario, argv[2]);
            printf("intento %d/%d: usuario=%s clave=%s...\n", i + 1, INTENTOS, usuario, clave);
            intento_ssh(destino, clave);
            sleep(PAUSA);
        }
        printf("listo — revisa el dashboard del servidor\n");
    }

    // modo FTP — igual, rota entre varias credenciales comunes en cada intento
    else if (strcmp(modo, "ftp") == 0)
    {
        if (argc < 3) { printf("falta el host\nuso: %s ftp <host>\n", argv[0]); return 1; }
        printf("simulando ataque de fuerza bruta FTP contra %s — %d intentos\n", argv[2], INTENTOS);
        for (int i = 0; i < INTENTOS; i++)
        {
            const char *usuario = usuarios[i % NUM_CREDENCIALES];
            const char *clave   = claves[i % NUM_CREDENCIALES];
            printf("intento %d/%d: usuario=%s clave=%s...\n", i + 1, INTENTOS, usuario, clave);
            intento_ftp(usuario, clave);
            sleep(PAUSA);
        }
        printf("listo — revisa el dashboard del servidor\n");
    }

    // modo CPU — estresa todos los nucleos del sistema
    else if (strcmp(modo, "cpu") == 0)
    {
        estresar_cpu();
        printf("estres de CPU terminado\n");
    }

    // modo RAM — consume un porcentaje alto de memoria
    else if (strcmp(modo, "ram") == 0)
    {
        estresar_ram();
        printf("estres de RAM terminado\n");
    }

    else
    {
        printf("modo desconocido: %s\n\n", modo);
        uso(argv[0]);
        return 1;
    }

    return 0;
}

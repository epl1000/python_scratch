
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>

#define BUFFER_SIZE 4096

int main() {
    int server_socket = socket(AF_INET, SOCK_STREAM, 0);
    if (server_socket < 0) {
        perror("socket() failed");
        return 1;
    }

    sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(8080);
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);

    if (bind(server_socket, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
        perror("bind() failed");
        close(server_socket);
        return 1;
    }

    if (listen(server_socket, SOMAXCONN) < 0) {
        perror("listen() failed");
        close(server_socket);
        return 1;
    }

    printf("Server is listening on port 8080...\n");

    while (1) {
        int client_socket = accept(server_socket, NULL, NULL);
        if (client_socket < 0) {
            perror("accept() failed");
            break;
        }

        char header[256];
        recv(client_socket, header, sizeof(header), 0);

        char *file_name = strtok(header, "|");
        long file_size = strtol(strtok(NULL, "|"), NULL, 10);

        FILE *file = fopen(file_name, "wb");
        if (!file) {
            perror("Unable to open file");
            break;
        }

        char buffer[BUFFER_SIZE];
        ssize_t bytes_received;
        while (file_size > 0 && (bytes_received = recv(client_socket, buffer, BUFFER_SIZE, 0)) > 0) {
            fwrite(buffer, 1, bytes_received, file);
            file_size -= bytes_received;
        }

        fclose(file);
        printf("Received file: %s\n", file_name);
        close(client_socket);
    }

    close(server_socket);
    return 0;
}

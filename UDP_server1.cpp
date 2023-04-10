#include <stdio.h>    // printf
#include <string.h>   // memset
#include <stdlib.h>   // exit
#include <arpa/inet.h>
#include <sys/socket.h>
#include <assert.h>

// Macros for ToFromPcStruct
#define ARRAY_SIZE(x) (sizeof(x)/sizeof(x[0]))
#define zero_this()   ::memset(this, 0, sizeof(*this))
#define zero_obj(x)   ::memset(&x, 0, sizeof(x))
#define zero_buff(x)  ::memset(x, 0, sizeof(x))

// Constants and struct for ToFromPcStruct
const int OMNI200_KEY_HOST_TO_OMNI = 0x484F5354; // "HOST"
const int OMNI200_KEY_OMNI_TO_HOST = 0x4F4D4E49; // "OMNI"
const int OMNI_UDP_ID_PORT = 57720;
const ulong OMNI_CONFIG_READ  = 0x52454144; // READ
const ulong OMNI_CONFIG_WRITE = 0x57524954; // WRITE
const int IPSETUP_DESC_LEN = 14;
const int IPSETUP_SN_LEN   = 8;

typedef unsigned long ulong;
typedef unsigned char uchar;

struct ToFromPcStruct {
    ulong byte_order;
    ulong key;
    ulong action;
    uchar ip_addr[4];
    uchar ip_mask[4];
    uchar ip_gw[4];
    uchar mac_addr[6];
    char desc[IPSETUP_DESC_LEN];
    char sn[IPSETUP_SN_LEN];
    ulong reserved[3];
public:
    ToFromPcStruct() {
        assert(sizeof(*this) == 64);
        zero_this();
        byte_order = 0x12345678;
    }

    void swapBytes() {
        ::bswap(&byte_order);
        ::bswap(&key);
        ::bswap(&action);
    }

    bool operator ==(const ToFromPcStruct& rhs) const {
        bool mac_ok = ::memcmp(mac_addr, rhs.mac_addr, sizeof(mac_addr)) == 0;
        bool ip_ok  = ::memcmp(ip_addr,  rhs.ip_addr,  sizeof(ip_addr) ) == 0;
        return mac_ok && ip_ok;
    }

    bool isOmniMAC() const {
        return mac_addr[0] == 0x00 && mac_addr[1] == 0x14 && mac_addr[2] == 0xB3;
    }
};

void die(char *s) {
    perror(s);
    exit(1);
}

int main(void) {
    struct sockaddr_in si_me, si_other;
    int s, slen = sizeof(si_other), recv_len;
    char buf[512]; // Max length of buffer

    // Create a UDP socket
    if ((s=socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)) == -1) {
        die("socket");
    }

    // Zero out the structure
    memset((char *) &si_me, 0, sizeof(si_me));
    si_me.sin_family = AF_INET;
    si_me.sin_port = htons(OMNI_UDP_ID_PORT); // Use defined port 57720
	si_me.sin_addr.s_addr = htonl(INADDR_ANY);
	
	// Bind socket to port
if (bind(s, (struct sockaddr*)&si_me, sizeof(si_me)) == -1) {
    die("bind");
}

// Keep listening for data
while (1) {
    printf("Waiting for data...");
    fflush(stdout);

    // Try to receive some data, this is a blocking call
    if ((recv_len = recvfrom(s, buf, sizeof(buf), 0, (struct sockaddr *) &si_other, &slen)) == -1) {
        die("recvfrom()");
    }

    // Print details of the client/peer and the data received
    printf("Received packet from %s:%d\n", inet_ntoa(si_other.sin_addr), ntohs(si_other.sin_port));
    printf("Data: %s\n", buf);

    // Fill in the ToFromPcStruct with mock values
    ToFromPcStruct resp;
    resp.action = OMNI_CONFIG_READ;
    resp.byte_order = 0x12345678;
    resp.key = OMNI200_KEY_OMNI_TO_HOST;
    resp.ip_addr[0] = 192; resp.ip_addr[1] = 168; resp.ip_addr[2] = 1; resp.ip_addr[3] = 2; // Mock IP address
    resp.ip_mask[0] = 255; resp.ip_mask[1] = 255; resp.ip_mask[2] = 255; resp.ip_mask[3] = 0; // Mock subnet mask
    resp.ip_gw[0] = 192; resp.ip_gw[1] = 168; resp.ip_gw[2] = 1; resp.ip_gw[3] = 1; // Mock gateway address
    resp.mac_addr[0] = 0x00; resp.mac_addr[1] = 0x14; resp.mac_addr[2] = 0xB3; // Mock MAC address
    resp.mac_addr[3] = 0xDE; resp.mac_addr[4] = 0xAD; resp.mac_addr[5] = 0xBE; // Mock MAC address
    strcpy(resp.desc, "OMNI-200");
    sprintf(resp.sn, "%05d", 12345); // Mock serial number

    // Now reply to the client with the filled ToFromPcStruct
    if (sendto(s, &resp, sizeof(resp), 0, (struct sockaddr*) &si_other, slen) == -1) {
        die("sendto()");
    }
}

close(s);
return 0;

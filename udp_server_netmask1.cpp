#include <ifaddrs.h>   // for getifaddrs
#include <net/if.h>    // for ifreq
#include <netinet/in.h>
#include <sys/ioctl.h> // for ioctl
#include <netdb.h>     // for getnameinfo
#include <unistd.h>

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
        byte_order = htonl(byte_order);
        key = htonl(key);
        action = htonl(action);
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

bool get_interface_info(char* if_name, uchar* ip_addr, uchar* mac_addr, uchar* ip_mask) {
    struct ifreq ifr;
    int fd = socket(AF_INET, SOCK_DGRAM, IPPROTO_IP);
    if (fd == -1) {
        return false;
    }

    strncpy(ifr.ifr_name, if_name, IFNAMSIZ-1);
    if (ioctl(fd, SIOCGIFADDR, &ifr) == 0) {
        struct sockaddr_in* ipaddr = (struct sockaddr_in*)&ifr.ifr_addr;
        memcpy(ip_addr, &ipaddr->sin_addr.s_addr, 4);
    } else {
        close(fd);
        return false;
    }



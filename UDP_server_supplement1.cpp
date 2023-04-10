clude <ifaddrs.h>   // for getifaddrs
#include <net/if.h>    // for ifreq
#include <netinet/in.h>
#include <sys/ioctl.h> // for ioctl
#include <netdb.h>     // for getnameinfo

// [Other includes and code remain unchanged]

bool get_interface_info(char* if_name, uchar* ip_addr, uchar* mac_addr) {
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

    if (ioctl(fd, SIOCGIFHWADDR, &ifr) == 0) {
        memcpy(mac_addr, ifr.ifr_hwaddr.sa_data, 6);
    } else {
        close(fd);
        return false;
    }

    close(fd);
    return true;
}

int main(void) {
    // [Other code remains unchanged]

    // Get network interface information
    struct ifaddrs* ifaddr, *ifa;
    char if_name[IFNAMSIZ];
    uchar ip_addr[4] = {0};
    uchar mac_addr[6] = {0};
    bool info_retrieved = false;

    if (getifaddrs(&ifaddr) == 0) {
        for (ifa = ifaddr; ifa != NULL; ifa = ifa->ifa_next) {
            if (ifa->ifa_addr == NULL || ifa->ifa_addr->sa_family != AF_INET) {
                continue;
            }
            if (strcmp(ifa->ifa_name, "lo") == 0) {
                continue;
            }
            strncpy(if_name, ifa->ifa_name, IFNAMSIZ-1);
            if (get_interface_info(if_name, ip_addr, mac_addr)) {
                info_retrieved = true;
                break;
            }
        }
        freeifaddrs(ifaddr);
    }

    // Keep listening for data
    while (1) {
        // [Other code remains unchanged]

        // Fill in the ToFromPcStruct
        ToFromPcStruct resp;
        resp.action = OMNI_CONFIG_READ;
        resp.byte_order = 0x12345678;
        resp.key = OMNI200_KEY_OMNI_TO_HOST;
        if (info_retrieved) {
            memcpy(resp.ip_addr, ip_addr, 4); // Use retrieved IP address
            memcpy(resp.mac_addr, mac_addr, 6); // Use retrieved MAC address
        } else {
            // Fallback to hardcoded values if interface info not retrieved
            resp.ip_addr[0] = 192; resp.ip_addr[1] = 168; resp.ip_addr[2] = 1; resp.ip_addr[3] = 2;
            resp.mac_addr[0] = 0x00; resp.mac_addr[1] = 0x14; resp.mac_addr[2] = 0; resp.mac_addr[3] = 0xDE; 
			resp.mac_addr[4] = 0xAD; resp.mac_addr[5] = 0xBE; // Mock MAC address
			esp.ip_mask[0] = 255; resp.ip_mask[1] = 255; resp.ip_mask[2] = 255; resp.ip_mask[3] = 0; // Mock subnet mask
			resp.ip_gw[0] = 192; resp.ip_gw[1] = 168; resp.ip_gw[2] = 1; resp.ip_gw[3] = 1; // Mock gateway address
		}				
		strcpy(resp.desc, "OMNI-200");
		sprintf(resp.sn, "%05d", 12345); // Mock serial number
		if (sendto(s, &resp, sizeof(resp), 0, (struct sockaddr*) &si_other, slen) == -1) 
		{
			die("sendto()");
		}
	}
	close(s);
	return 0;
}

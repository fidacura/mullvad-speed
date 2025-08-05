#!/usr/bin/env python3
import requests                             # for making http requests to mullvad api
import socket                               # for testing connection times
import sys                                  # for system stuff like exit
import time                                 # for measuring ping times
from typing import List, Dict, Optional     # for type hints (makes code more robust)
from rich.console import Console            # for pretty console output
from rich.table import Table                # for creating nice looking tables
from concurrent.futures import ThreadPoolExecutor, as_completed  # for running tests in parallel

class MullvadSpeedTest:
    def __init__(self):
        # mullvad's api endpoint
        self.api_url = "https://api.mullvad.net/www/relays/all/"
        # initialize rich console for pretty output (colors, tables, etc)
        self.console = Console()
        # some headers to make our requests look legit
        self.headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

    def fetch_servers(self) -> List[Dict]:
        """fetch all available mullvad servers"""
        try:
            # get the server list with a 5 second timeout
            response = requests.get(self.api_url, timeout=5, headers=self.headers)
            response.raise_for_status()  # will raise an error if request fails
            
            # filter to get only active wireguard servers
            servers = [s for s in response.json() if s['type'] == 'wireguard' and s.get('active', False)]
            self.console.print(f"[green]found {len(servers)} active wireguard servers")
            return servers
        except Exception as e:
            # if something goes wrong, show error and quit
            self.console.print(f"[red]error fetching servers: {str(e)}")
            sys.exit(1)

    def ping_server(self, server: Dict) -> Optional[Dict]:
        """measure ping time to a server by trying to connect to it"""
        hostname = server.get('hostname', '')
        try:
            # get the server's ip address
            ip = server.get('ipv4_addr_in')
            if not ip:
                return None
            
            # test connection 3 times and take average for more accurate results
            pings = []
            for _ in range(3):
                start_time = time.time()
                # try to connect to port 443 (https) with 2 second timeout
                socket.create_connection((ip, 443), timeout=2)
                pings.append((time.time() - start_time) * 1000)  # convert to milliseconds
            
            # calculate average ping
            avg_ping = sum(pings) / len(pings)
            
            # return all the useful info about server
            return {
                'hostname': hostname,
                'country': server.get('country_name', server.get('country_code', 'Unknown')),
                'city': server.get('city_name', server.get('city_code', 'Unknown')),
                'ping_ms': round(avg_ping, 2),  # round to 2 decimal places
                'provider': server.get('provider', 'Unknown'),
                'owned': server.get('owned', False),  # whether mullvad owns the server
                'load': server.get('load', 0),
                'port_speed': server.get('network_port_speed', 0),  # network speed in gbps
                'ipv4_addr': server.get('ipv4_addr_in', 'Unknown'),
                'stboot': server.get('stboot', False),  # secure boot status
                'ipv6': bool(server.get('ipv6_addr_in')),  # has ipv6 support?
                'multihop_port': server.get('multihop_port'),  # port for multi-hop connections
                'socks_available': bool(server.get('socks_name'))  # has socks proxy?
            }
        except Exception:
            # if we can't connect, skip server
            return None

    def test_servers(self, max_results: int = 10) -> List[Dict]:
        """test all servers and return top results based on ping time"""
        # get the list of all servers
        servers = self.fetch_servers()
        results = []
        
        self.console.print("[yellow]testing server response times...")
        # use threadpoolexecutor to test multiple servers at once (way faster!)
        with ThreadPoolExecutor(max_workers=10) as executor:
            # start tests
            future_to_server = {executor.submit(self.ping_server, server): server for server in servers}
            completed = 0
            
            # as each test completes, collect its results
            for future in as_completed(future_to_server):
                completed += 1
                # show progress (overwrite line with \r)
                self.console.print(f"progress: {completed}/{len(servers)}", end='\r')
                
                result = future.result()
                if result:
                    results.append(result)
        
        # sort by ping time and return the top ones
        return sorted(results, key=lambda x: x['ping_ms'])[:max_results]

    def display_results(self, results: List[Dict]):
        """show the results in a nice table"""
        if not results:
            self.console.print("[red]no valid test results found")
            return

        # create a table with all columns
        table = Table(title="mullvad server speed test results")
        table.add_column("Hostname", style="yellow", no_wrap=True)
        table.add_column("Location", style="cyan")
        table.add_column("IPv4", style="blue", no_wrap=True)
        table.add_column("Ping", justify="right", style="green")
        table.add_column("Speed", justify="right", style="magenta")
        table.add_column("Owned", justify="center", style="red")
        table.add_column("Features", style="cyan")

        # add each server to the table
        for result in results:
            # collect all the feats this server supports
            features = []
            if result['ipv6']:
                features.append("IPv6")
            if result['stboot']:
                features.append("SecureBoot")
            if result['socks_available']:
                features.append("SOCKS")
            if result['multihop_port']:
                features.append("MultiHop")
            
            # join features with commas or show dash if none
            features_str = ", ".join(features) if features else "-"
            
            # format location and port speed
            location = f"{result['city']}, {result['country']}"
            port_speed = f"{result['port_speed']}Gbps" if result['port_speed'] else "Unknown"
            
            # add row to table
            table.add_row(
                result['hostname'],
                location,
                result['ipv4_addr'],
                f"{result['ping_ms']}ms",
                port_speed,
                str(result['owned']).lower(),
                features_str
            )

        # print a newline to clear the progress counter
        self.console.print("\n")
        # show table
        self.console.print(table)
        
        # get info about the best server (first one since they're sorted)
        best = results[0]
        features = []
        if best['ipv6']: features.append("IPv6 support")
        if best['stboot']: features.append("secure boot")
        if best['socks_available']: features.append("SOCKS proxy")
        if best['multihop_port']: features.append("multi-hop capable")
        
        # add features in parentheses if any exist
        features_str = f" ({', '.join(features)})" if features else ""
        
        # show the recommendation
        self.console.print(f"\n[bold green]recommended server:[/bold green] "
                          f"{best['hostname']} in {best['city']}, {best['country']}\n"
                          f"IPv4: {best['ipv4_addr']}\n"
                          f"Ping: {best['ping_ms']} ms\n"
                          f"Port Speed: {best['port_speed']} Gbps\n"
                          f"Owned by Mullvad: {str(best['owned']).lower()}"
                          f"{features_str}")

def main():
    # how many servers to show (default 10)
    max_results = 10
    # check if user specified a different number
    if len(sys.argv) > 1:
        try:
            max_results = int(sys.argv[1])
        except ValueError:
            print(f"error: invalid number of servers. using default: {max_results}")

    # create our tester, run the tests, and show the results
    tester = MullvadSpeedTest()
    results = tester.test_servers(max_results=max_results)
    tester.display_results(results)

if __name__ == "__main__":
    main()
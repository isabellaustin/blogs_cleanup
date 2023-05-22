import requests
import json
import sys
from wordpress import wp
import colorama
from colorama import Fore, Back
import mysql.connector

def main(name: str = "World") -> None:
    """This is the main function for this program. It prints Hello and takes a name.

    Args:
        name (str, optional): This should be a single name. Defaults to "World".
    """    
    colorama.init(autoreset=True)

    print(f"Hello {name}")


if __name__ == "__main__":
    stats = {}




    cnx = mysql.connector.connect(user="wordpress", password="4AbyJVrcPTH6aHgfAqt3", host="mysql-1.butler.edu", database="wp_blogs_dev")
    
    with open('config.json', 'r') as f:
        cfg=json.load(f)
        exclude_users = cfg["exclude_users"]
        exclude_outside_users = cfg["exclude_outside_users"]

    blogs = wp(url = cfg["url"],
                username = cfg["username"],
                password = cfg["password"])
 
    # data = blogs.get_users()
    # for d in data:
    #     print(d)
    #============================================================================================================================================
    
    outside_users = {}
    blogs.get_outside_users(outside_users, cnx)
    data = outside_users.values()
    with open("outside_users.txt", "w") as f:
        for d in data:
            if d not in exclude_outside_users:
                f.write("%s\n" % d)    

    # #============================================================================================================================================

    id_username = {}
    blogs.get_id_username(id_username, cnx)

    data = blogs.get_inactive_users(exclude = exclude_users, blogs_users=id_username.values()) #all butler users that

    #============================================================================================================================================

    user_blogs = {}
    blogs.get_user_blogs(user_blogs, cnx)

    sites = user_blogs.values()

    for site in sites:
        stats[site] = {"remove":0, "keep":0}
        site_users = blogs.get_site_users(site)
        remaining_users = len(site_users)
        # if id_username not in site_users:
        #     print(f"{Fore.WHITE}{Back.BLACK}{id_username} not a butler user{Back.RESET}")
        for u in site_users:
            try:
                username = id_username[u]
            except KeyError as KE:
                continue
            if username in data: 
                print(f"{Fore.RED}{username} will be removed from {site}")
                remaining_users-=1
                stats[site]["remove"]+=1
            else:
                print(f"{Fore.GREEN}{username} will not be removed from {site}")
                stats[site]["keep"]+=1
        
        if remaining_users == 0:
             print(f"{Back.RED}{site} has no remaining users and will be archived{Back.RESET}")

    # #============================================================================================================================================
    
    cnx.close()

    print(stats) # fancy, how many sites do/do not have users left
import requests
import json
import sys
from wordpress import wp
import colorama  # for colorama.init
from colorama import Fore, Back
import mysql.connector

def main(blogs) -> None:
    
    # STATS
    site_stats = {} #tracks whether a site is kept or archived
    indv_user_stats = {} #tracks users on one site

    overall_kept_sites = 0
    overall_del_sites = 0
    overall_kept_users = 0
    overall_del_users = 0

    sites_tbd = [] #blogs to be deleted
    users_tbd = [] #users to be deleted
    # keyErr_users = []

#NEW FUNC =======================================================================================================================================

    """creates a file with a list of non-Butler users (i.e. users with emails that don't end in '@butler.edu')"""    
    outside_users = {}
    blogs.get_outside_users(outside_users, cnx)
    outside_data = outside_users.values()
    with open("outside_users.txt", "w") as f:
        for d in outside_data:
            if d not in exclude_outside_users:
                f.write("%s\n" % d)    

    """creates a list of ids and usernames of blogs users with Butler emails"""    
    id_username = {}
    blogs.get_id_username(id_username, cnx)

    """creates a list of inactive users by finding the difference between the list of current users (created id_username list) 
        and all active users"""
    inactive_data = blogs.get_inactive_users(exclude = exclude_users, blogs_users=id_username.values())

#NEW FUNC =======================================================================================================================================

    """creates a list of blogs in the database"""
    user_blogs = {}
    blogs.get_user_blogs(user_blogs, cnx)
    sites = user_blogs.values()
    
    for site in sites:
        site_stats[site] = {"archive":0, "keep":0}
        indv_user_stats[site] = {"remove":0, "keep":0}

        """gets the list of users on a site"""        
        site_users = blogs.get_site_users(site)
        remaining_users = len(site_users)

        for u in site_users:
            username = id_username[u]

            if username in inactive_data: #if user is inactive
                print(f"{Fore.RED}{username} will be removed from {site}")
                
                remaining_users-=1
                overall_del_users+=1
                indv_user_stats[f"{site}"]["remove"]+=1
                users_tbd.append(f"{username}")             
            else:
                print(f"{Fore.GREEN}{username} will not be removed from {site}")

                indv_user_stats[f"{site}"]["keep"]+=1
        if remaining_users == 0:
            print(f"{Fore.WHITE}{Back.RED}{site} has no remaining users and will be archived{Back.RESET}")

            site_stats[f"{site}"]["archive"]+=1
            overall_del_sites+=1
            sites_tbd.append(f"{site}") 
        else:
            site_stats[f"{site}"]["keep"]+=1
            overall_kept_sites+=1
            overall_kept_users+=remaining_users

        # print(f"The amount of users removed from {site}: {indv_user_stats[site]['remove']}")
        # print(f"The amount of remaining on {site}: {indv_user_stats[site]['keep']}")
    
    cnx.close()
    deletion(cnx, id_username, users_tbd, sites_tbd)
    get_stats(inactive_data, outside_data, sites, overall_kept_sites, overall_del_sites, overall_kept_users, overall_del_users)


def deletion(mysql, id_username, users, sites) -> None:
    # print(users_tbd)
    # print(sites_tbd)

    # DELETE USERS
    """deleting the inactive users across all blogs"""    
    # for u in users: #users_tbd
    #     try:
    #         username = id_username[u]
    #     except KeyError as KE:
    #         continue
    #     # print(u)
    #     blogs.delete_user(u, username, cnx) #id, user_login
    #     print(f"{Back.GREEN}User {username} was deleted from the database.{Back.RESET}")

    # DELETE SITES
    """deleting abandoned blogs"""    
    # for u in sites: #sites_tbd
    #     try:
    #         path = sites[u]
    #     except KeyError as KE:
    #         continue
    #     blogs.delete_blog(u, path, cnx) #blog_id, path
    #     print(f"{Back.GREEN}Blog {path} was deleted from the database.{Back.RESET}")

   
def get_stats(inactive, outside, sites, kept_sites, del_sites, kept_users, del_users) -> None:
    """output statisitics"""    
    # BLOGS
    print(f"Initial amount of sites: {len(sites)}")

    print(f"Amount of sites kept: {kept_sites}")
    print(f"Amount of sites archived: {del_sites}")

    perc_blog_cleanup = (del_sites / len(sites)) * 100
    print(f"Percent decrease in blogs: {perc_blog_cleanup}%")

    # USERS
    total_bu_users = kept_users + del_users
    print(f"Initial amount of Butler users across all sites: {total_bu_users}")
    print(f"Amount of inactive Butler users across all sites: {len(inactive)}")
    print(f"Amount of non-Butler users across all sites: {len(outside)}")
    
    print(f"Amount of Butler users remaining across all sites: {kept_users}")
    print(f"Amount of Butler users removed across all sites: {del_users}")
    print(f"Amount of non-Butler users removed (?) across all sites: {len(outside)}") # are all non butler users being removed?

    perc_user_cleanup = (del_users / total_bu_users) * 100
    print(f"Percent decrease in Butler users: {perc_user_cleanup}%")


if __name__ == "__main__":
    colorama.init(autoreset=True)
    cnx = mysql.connector.connect(user="wordpress", password="4AbyJVrcPTH6aHgfAqt3", host="mysql-1.butler.edu", database="wp_blogs_dev")
    
    with open('config.json', 'r') as f:
        cfg=json.load(f)
        exclude_users = cfg["exclude_users"]
        exclude_outside_users = cfg["exclude_outside_users"]

    blogs = wp(url = cfg["url"],
                username = cfg["username"],
                password = cfg["password"])
    
    main(blogs)
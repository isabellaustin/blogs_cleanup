import requests
import json
import sys
from wordpress import wp
import colorama  # for colorama.init
from colorama import Fore, Back
import mysql.connector
from tqdm.auto import tqdm
import logging

def main(blogs) -> None:
    """stat variables"""
    all_kept_sites = 0
    all_del_sites = 0

    all_kept_users = []
    all_kept_users_unique = []
    all_del_users = []
    all_del_users_unique = []

    #tbd: to be deleted
    sites_tbd = {}
    users_tbd = {}

    elapsed = []
    sum_elapsed = 0

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

    """creates a list of blogs in the database"""
    user_blogs = {}

    blogs.get_user_blogs(user_blogs, cnx)
    sites = list(user_blogs.keys()) #gets site id

    for site in sites: #tqdm(sites[:1000], position=0):
        """gets the list of users on a site"""        
        site_users = blogs.get_site_users(site, cnx) #necessary sites aren't excluded, such as buwebservices
        remaining_users = len(site_users)
        site_path = user_blogs[site]
         
        for u in site_users: 
            username = id_username[u] # key: id, value: username

            if username in inactive_data: #if user is inactive
                print(f"{Fore.RED}{username} will be removed from {site_path}")
            
                # users_tbd.append(f"{username}")
                users_tbd[username] = u # key: username, value: id
                remaining_users-=1

                all_del_users.append(f"{username}")
                if username not in all_del_users_unique: 
                    all_del_users_unique.append(f"{username}")            
            else:
                print(f"{Fore.GREEN}{username} will not be removed from {site_path}")

                all_kept_users.append(f"{username}")
                if username not in all_kept_users_unique: 
                    all_kept_users_unique.append(f"{username}")

        if remaining_users == 0:
            print(f"{Fore.WHITE}{Back.RED}{site_path} has no remaining users and will be archived{Back.RESET}")

            all_del_sites+=1
            # sites_tbd.append({site_path}) 
            sites_tbd[site_path] = site # key: path, value: id
        else:
            all_kept_sites+=1

        index_num = int(list(sites).index(site)) + 1 #starts at 1 instead of 0
        print(f"SITE {index_num} OF {len(sites)}")    # prints out "site x of 8610"

    blog_deletion(sites_tbd)
    user_deletion(users_tbd)

    cnx.close()

    get_stats(inactive_data, outside_data, sites, all_kept_sites, all_del_sites, all_kept_users, all_del_users, all_kept_users_unique, elapsed, sum_elapsed)


def blog_deletion(sites_tbd) -> None:
    """archiving blogs if they are abandoned, otherwise, deleting necessary users"""  
    #  site should already have zero users if its been put into the  sites_tbd list

    sites = list(sites_tbd.keys())

    for site in sites:
        # print(sites_tbd[site])
        
        # blogs.archive_blog(sites_tbd[site]) #sites_tbd[site] = blog_id
        # sites_tbd.pop(f"{site}")

        print(f"{Fore.WHITE}{Back.GREEN}Blog {site} was archived.{Back.RESET}")


def user_deletion(users_tbd) -> None:
    """deleting the inactive users across all blogs and reassigning their content to buwebservices""" 
    # buwebservices numeric ID = 9197309
    # https://developer.wordpress.org/cli/commands/user/delete/
    
    users = list(users_tbd.keys())  
           
    for u in users:
        # print(users_tbd[u])

        # blogs.create_user("buwebservices")
        # blogs.reassign_user(u, 9197309) # reassigns and deletes, can you reassign without deleting
        # blogs.network_del_user(u)

        # users_tbd.pop(f"{u}") # removes user from users_tbd list

        print(f"{Fore.WHITE}{Back.GREEN}User {u} was deleted from the database.{Back.RESET}")


def get_stats(inactive, outside, sites, kept_sites, del_sites, kept_users, del_users, kept_unique, elapsed, sum_elapsed) -> None:
    logger.setLevel(logging.INFO)
    
    """output statisitics"""    
    # INITIAL
    total_bu_users = len(kept_users) + len(del_users)
    logger.info(f"Initial number of Butler users across all sites: {total_bu_users}")
    logger.info(f"Initial number of sites: {len(sites)}")
    logger.info(f"Number of inactive Butler users across all sites: {len(inactive)}")
    logger.info(f"Number of non-Butler users across all sites: {len(outside)}\n")
    
    # REMAINING 
    logger.info(f"Number of sites remaining: {kept_sites}")
    logger.info(f"Number of Butler users remaining across all sites: {len(kept_users)}\n")

    # CLEANUP
    logger.info(f"Number of sites archived: {del_sites}")
    logger.info(f"Number of Butler users removed across all sites: {len(del_users)}")
    logger.info(f"Number of non-Butler users removed (?) across all sites: {len(outside)}\n") # are all non butler users being removed?
    
    # STATISTICS
    total_net_users = len(inactive) + len(kept_unique)
    logger.info(f"Total number of Butler users in the network: {total_net_users} ({len(inactive)} inactive, {len(kept_unique)} active)")

    perc_blog_cleanup = (del_sites / len(sites)) * 100
    perc_bformat = '{:.2f}'.format(perc_blog_cleanup)
    logger.info(f"Percent decrease in blogs: {perc_bformat}%")

    perc_user_cleanup = (len(del_users) / total_bu_users) * 100
    perc_uformat = '{:.2f}'.format(perc_user_cleanup)
    logger.info(f"Percent decrease in Butler users: {perc_uformat}%")


if __name__ == "__main__":
    colorama.init(autoreset=True)
    cnx = mysql.connector.connect(user="wordpress", password="4AbyJVrcPTH6aHgfAqt3", host="docker-dev.butler.edu", database="wp_blogs_dev")
    
    with open('config.json', 'r') as f:
        cfg=json.load(f)
        exclude_users = cfg["exclude_users"]
        exclude_outside_users = cfg["exclude_outside_users"]

    blogs = wp(url = cfg["url"],
                username = cfg["username"],
                password = cfg["password"])
    
    log_file = cfg['log_file']
    logger = logging.getLogger(__name__)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh = logging.FileHandler(log_file, mode='w')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    main(blogs)
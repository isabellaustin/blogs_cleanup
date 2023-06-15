import requests
import json
import sys
from wordpress import wp
import colorama  # for colorama.init
from colorama import Fore, Back
import mysql.connector
from tqdm.auto import tqdm
import logging
import csv

"""stat variables"""
all_kept_users = []
all_kept_users_unique = []
all_del_users = []
all_del_users_unique = []
all_other_del = []
all_other_del_unique = []
    #tbd: to be deleted
sites_tbd = {}
users_tbd = {}
other_users_tbd = {}
key = []

empty = []


def main(blogs) -> None:
    all_kept_sites = 0
    all_del_sites = 0

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
    inactive_data = blogs.get_inactive_users(exclude = exclude_all_users, blogs_users=id_username.values())

    """creates a list of blogs in the database"""
    user_blogs = {}

    blogs.get_user_blogs(user_blogs, cnx)
    sites = list(user_blogs.keys()) #gets site id
# '''
    for site in sites: #tqdm(sites[:1000], position=0):
        """gets the list of users on a site"""        
        site_users = blogs.get_site_users(site, cnx)
        remaining_users = len(site_users)
        site_path = user_blogs[site]
         
        for u in site_users: 
            username = id_username[u] # key: id, value: username

            if username in inactive_data: #if user is inactive
                print(f"{Fore.RED}{username} will be removed from {site_path}{Fore.RESET}")

                remaining_users-=1

                if username in outside_data: #non-BU deleted
                    other_users_tbd[username] = u # key: username, value: id

                    all_other_del.append(username)
                    if username not in all_other_del_unique: 
                        all_other_del_unique.append(username)
                else:                       #BU deleted
                    users_tbd[username] = u # key: username, value: id

                    all_del_users.append(username)
                    if username not in all_del_users_unique: 
                        all_del_users_unique.append(username) 
            else:
                print(f"{Fore.GREEN}{username} will not be removed from {site_path}{Fore.RESET}")

                all_kept_users.append(username)
                if username not in all_kept_users_unique: 
                    all_kept_users_unique.append(username)

        if remaining_users == 0:
            print(f"{Fore.WHITE}{Back.RED}{site_path} has no remaining users and will be archived{Back.RESET}")

            all_del_sites+=1
            sites_tbd[site_path] = site # key: path, value: id
        else:
            all_kept_sites+=1

        index_num = int(list(sites).index(site)) + 1    #starts at 1 instead of 0
        print(f"SITE {index_num} OF {len(sites)}")

    fetch_user_sites(outside_users)
    blog_deletion()
    user_deletion(outside_users)

    cnx.close()

    get_stats(inactive_data, outside_data, sites, all_kept_sites, all_del_sites)
# '''

def blog_deletion() -> None:
    """archiving blogs if they are abandoned, otherwise, deleting necessary users"""  
    #  site should already have zero users if its been put into the  sites_tbd list

    sites = list(sites_tbd.keys())

    for site in sites:
        blog_id = sites_tbd[site]

        # blogs.archive_blog(blog_id)
        # sites_tbd.pop(site)

        print(f"{Fore.WHITE}{Back.RED}BLOG {site} was archived.{Back.RESET}{Fore.RESET}")


def delete_user(user_id) -> None:
    # buwebservices numeric ID = 9197309
    # https://developer.wordpress.org/cli/commands/user/delete/

    blogs.create_user("buwebservices")
    blogs.reassign_user(user_id, 9197309) # reassigns and deletes, can you reassign without deleting
    blogs.network_del_user(user_id)


def user_deletion(outside_users) -> None:
    """deleting the inactive users across all blogs and reassigning their content to buwebservices"""     
    users = list(users_tbd.keys()) #BU    
    for u in users:
        id = users_tbd[u]

        # delete_user(id)
        # users_tbd.pop(u) # removes user from users_tbd list

        print(f"(Butler){Fore.WHITE}{Back.RED} USER {u} was deleted from the database.{Back.RESET}{Fore.RESET}") 

    other_users = list(other_users_tbd.keys())    
    outside_values = list(outside_users.values())
    for ou in outside_values:
        if ou not in other_users:       #non-BU users that were NOT on sites
            id = blogs.get_id_by_email(ou, cnx) 

            # delete_user(id)
            # outside_users.pop(username)
                
            all_other_del.append(ou)
            if ou not in all_other_del_unique: 
                all_other_del_unique.append(ou)

        elif ou in other_users:         #non-BU users that were on sites
            id = users_tbd[u]

            # delete_user(id)
            # other_users_tbd.pop(ou)

        print(f"(Non-Butler){Fore.WHITE}{Back.RED} USER {ou} was deleted from the database.{Back.RESET}{Fore.RESET}")

    # print(other_users_tbd)
    # print(len(other_users_tbd))

    # print(len(all_del_users_unique))
    # print(len(all_other_del_unique))


def get_stats(inactive, outside, sites, kept_sites, del_sites) -> None:
    logger.setLevel(logging.INFO)
    
    """output statisitics"""    
    # INITIAL
    # total_bu_users = len(all_kept_users_unique) + len(all_del_users_unique)
    # logger.info(f"Initial number of Butler users across all sites: {total_bu_users}")
    logger.info(f"Initial number of sites: {len(sites)}")

    total_net_users = len(inactive) + len(all_kept_users_unique)
    logger.info(f"Number of Butler users on the network: {total_net_users} ({len(inactive)} inactive, {len(all_kept_users_unique)} active)")
    logger.info(f"Number of non-Butler users on the network: {len(outside)} ({len(empty)} siteless)\n")
   
    # REMAINING 
    logger.info(f"Number of remaining sites: {kept_sites}")
    total_kept_users = len(all_kept_users_unique) + len(other_users_tbd)
    logger.info(f"Number of remaining users: {total_kept_users} ({len(all_kept_users_unique)} Butler, {len(other_users_tbd)} non-Butler)\n")

    # CLEANUP
    logger.info(f"Number of archived sites: {del_sites}")
    total_del_users = len(all_del_users_unique) + len(all_other_del_unique)
    logger.info(f"Number of deleted users: {total_del_users} ({len(all_del_users_unique)} Butler, {len(all_other_del_unique)} non-Butler)\n")

    # STATISTICS
    perc_blog_cleanup = (del_sites / len(sites)) * 100
    perc_bformat = '{:.2f}'.format(perc_blog_cleanup)
    logger.info(f"Percent decrease in blogs: {perc_bformat}%")

    perc_user_cleanup = (total_del_users / total_net_users) * 100
    perc_uformat = '{:.2f}'.format(perc_user_cleanup)
    logger.info(f"Percent decrease in Butler users: {perc_uformat}%")


def fetch_user_sites(outside_users) -> None:   
    header = ['user_email', 'num_of_sites'] 
    with open('sitestats.csv', 'w', encoding='UTF8') as f:
        writer = csv.writer(f)
        writer.writerow(header)

        outside_values = list(outside_users.values())
        for ou in outside_values:
            id = blogs.get_id_by_email(ou, cnx)
            lst = blogs.get_user_sites(id,cnx)
            
            if len(lst) == 0:
                empty.append(ou)
            # if len(lst) > 0:
            #     print(ou)
            #     print(lst)

            data = [f'{ou}', f'{len(lst)}']
            writer.writerow(data)


if __name__ == "__main__":
    colorama.init() #(autoreset=True)
    cnx = mysql.connector.connect(user="wordpress", password="4AbyJVrcPTH6aHgfAqt3", host="docker-dev.butler.edu", database="wp_blogs_dev")
    
    with open('config.json', 'r') as f:
        cfg=json.load(f)
        exclude_users = cfg["exclude_users"]
        exclude_outside_users = cfg["exclude_outside_users"]
        exclude_all_users = cfg["exclude_all_users"]

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
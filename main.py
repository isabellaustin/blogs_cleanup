from wordpress import wp
from data import d
import json
import mysql.connector
import colorama
from colorama import Fore, Back
import logging

all_kept_users_unique = []
all_del_users_unique = []
all_other_del_unique = []
inactive = []
user_dates = []
blogs_dates = []
nomads = [] #list of users without any sites
key = [] #error handling list
site_users_tbd = []
id_list = []
username_list = []

#tbd: to be deleted
sites_tbd = {}
users_tbd = {}
other_users_tbd = {}
abandoned_sites = {}
deletion_dict = {}
yearly_reg = {}
yearly_user_reg = {}

other_del_dict = {}



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

    """creates a list of ids and usernames of blogs users"""    
    id_username = {}
    blogs.get_id_username(id_username, cnx)
    id_list = list(id_username.keys())
    username_list = list(id_username.values())

    """creates a list of inactive users by finding the difference between the list of current users (created id_username list) 
        and all active users"""
    inactive_data = blogs.get_inactive_users(exclude = exclude_users, blogs_users=id_username.values())

    """creates a list of blogs in the database"""
    user_blogs = {}
    blogs.get_user_blogs(user_blogs, cnx)

    sites = list(user_blogs.keys()) #gets site id
    
    for site in sites:
        """gets the list of users on a site"""        
        
        site_users = blogs.get_site_users(site, cnx)

        remaining_users = len(site_users)
        site_path = user_blogs[site]
        # deletion_dict[site_path] = []
         
        for u in site_users: 
            username = id_username[u] # key: id, value: username
            # users_tbd[username] = []

            if username in inactive_data: #if user is inactive
                print(f"{Fore.RED}{username} will be removed from {site_path}{Fore.RESET}")

                remaining_users-=1

                if username in outside_data: #non-BU deleted
                    if username not in list(other_del_dict.keys()):
                        other_del_dict[site] = []
                    other_del_dict[site].append(u) # a dict of the sites non-BU users are on

                    other_users_tbd[username] = u # key: username, value: id

                    if username not in all_other_del_unique: 
                        all_other_del_unique.append(username)
                else:                       #BU deleted
                    users_tbd[username] = u # key: username, value: id
                    # deletion_dict[site_path].append(u)

                    if username not in all_del_users_unique: 
                        all_del_users_unique.append(username) 
            else:
                print(f"{Fore.GREEN}{username} will not be removed from {site_path}{Fore.RESET}")

                if username not in all_kept_users_unique: 
                    all_kept_users_unique.append(username)

        if remaining_users == 0:
            print(f"{Fore.WHITE}{Back.RED}{site_path} has no remaining users and will be archived{Fore.RESET}{Back.RESET}")
            deletion_dict[site_path] = site_users # a dict of users on sites that are tbd

            all_del_sites+=1
            sites_tbd[site_path] = site # key: path, value: id
        else:
            all_kept_sites+=1

        # print(deletion_dict)

        index_num = int(list(sites).index(site)) + 1    #starts at 1 instead of 0
        print(f"SITE {index_num} OF {len(sites)}")
    
    data.sitestats_csv(username_list,outside_users,nomads,cnx) #needs to run for 'siteless users' stats
    data.fetch_multisite_users(username_list,id_list, all_kept_users_unique,user_blogs,cnx)
    data.remove_multisite_admins()
    data.user_sitedata_csv(username_list,id_list,user_blogs,key,cnx)
    data.userdata_csv(username_list, id_list,user_dates,yearly_user_reg,cnx)
    data.sitedata_csv(username_list,id_list,user_blogs,blogs_dates,yearly_reg,key,cnx)
    data.plugins_csv(cnx)
    data.themes_csv(cnx)

    deletion(outside_users,user_blogs,id_username)
    cnx.close()
    get_stats(inactive_data, outside_data, sites, all_kept_sites, all_del_sites, id_username)


# DELETION ========================================================================================
def deletion(outside_users,user_blogs,id_username) -> None:
    """archiving blogs if they are abandoned, otherwise, deleting necessary users"""  
    #  site should already have zero users if its been put into the sites_tbd list

    # BU users on sites
    BU_sites = list(deletion_dict.keys())
    for site in BU_sites: 
        user_list = deletion_dict[site]
        # print(site, user_list)

        user_deletion(site, user_list)

        sites_tbd.pop(site)
        del deletion_dict[site]

    # non-BU users on sites
    non_BU_sites = list(other_del_dict.keys())
    for blog_id in non_BU_sites:
        user_list = other_del_dict[blog_id]
        site = user_blogs[blog_id]

        user_deletion(site, user_list)
        del other_del_dict[blog_id]

        # index = id_list.index(user_id)
        # username = username_list[index]

    #non-BU users NOT on sites
    non_BU_ids = list(outside_users.keys())
    for id in non_BU_ids:
        if id not in list(other_del_dict.keys()):
            # blogs.network_del_user(id)
            print("net del")

            username = id_username[id]
            if username not in all_other_del_unique: 
                all_other_del_unique.append(username)


def user_deletion(site, user_list) -> None:
    # add buwebservices (UID = 9197309) to site
    if 9197309 not in user_list:
        print(f"buwebservices not in {site}'s user list")
        # blogs.create_user(9197309, site)

    del_blog = True
    user_id_tbd = list(users_tbd.values())
    other_id_tbd = list(other_users_tbd.values())

    for user_id in user_list:
        if user_id in user_id_tbd or user_id in other_id_tbd:
            if user_id in user_id_tbd:
                index = user_id_tbd.index(user_id)
                username = list(users_tbd.keys())[index]
            else:
                index = other_id_tbd.index(user_id)
                username = list(other_users_tbd.keys())[index]

            # blogs.reassign_user(user_id, 9197309)
            print("reassign")
            # blogs.network_del_user(user_id)
            print("net del")

            print(f"(Butler){Fore.WHITE}{Back.RED} USER {username} was deleted from the network.{Back.RESET}{Fore.RESET}")
            
    if del_blog:
        if site in list(sites_tbd.keys()):
            blog_id = sites_tbd[site]
            
            # blogs.archive_blog(blog_id)
            print(f"{Fore.WHITE}{Back.RED}BLOG {site} was archived.{Back.RESET}{Fore.RESET}")
    else:
        print(f"BLOG {site} could not be archived.")


# STATISTICS ======================================================================================
def get_stats(inactive, outside, sites, kept_sites, del_sites, id_username) -> None:
    logger.setLevel(logging.INFO)
    
    """output statisitics"""    
    # INITIAL
    total_bu_users = len(all_kept_users_unique) + len(all_del_users_unique)
    # logger.info(f"Initial number of Butler users across all sites: {total_bu_users}")
    logger.info(f"Initial number of sites: {len(sites)}")
    active = len(id_username) - len(inactive) #total users: id_username
    logger.info(f"Initial number of users: {len(id_username)} ({len(inactive)} inactive, {active} active)\n")

 
    logger.info(f"Number of Butler users on the network: {total_bu_users} ({len(all_del_users_unique)} inactive, {len(all_kept_users_unique)} active)")
    logger.info(f"Number of non-Butler users on the network: {len(outside)} ({len(nomads)} siteless)\n")

    # CLEANUP
    logger.info(f"Number of archived sites: {del_sites}")
    total_del_users = len(all_del_users_unique) + len(all_other_del_unique)
    logger.info(f"Number of deleted users: {total_del_users} ({len(all_del_users_unique)} Butler, {len(all_other_del_unique)} non-Butler)\n")

    # REMAINING 
    logger.info(f"Number of remaining sites: {kept_sites}")
    total_kept_users = len(all_kept_users_unique) + len(other_users_tbd)
    logger.info(f"Number of remaining users: {total_kept_users} ({len(all_kept_users_unique)} Butler, {len(other_users_tbd)} non-Butler)\n")

    # STATISTICS
    perc_blog_cleanup = (del_sites / len(sites)) * 100
    perc_bformat = '{:.2f}'.format(perc_blog_cleanup)
    logger.info(f"Percent decrease in sites: {perc_bformat}%")

    perc_user_cleanup = (total_del_users / len(id_username)) * 100
    perc_uformat = '{:.2f}'.format(perc_user_cleanup)
    logger.info(f"Percent decrease in users: {perc_uformat}%")


# MAIN ============================================================================================
if __name__ == "__main__":
    colorama.init()
    cnx = mysql.connector.connect(user="wordpress", password="4AbyJVrcPTH6aHgfAqt3", host="docker-dev.butler.edu", database="wp_blogs_dev")
    
    with open('config.json', 'r') as f:
        cfg=json.load(f)
        exclude_users = cfg["exclude_users"]
        exclude_outside_users = cfg["exclude_outside_users"]
        exclude_all_users = cfg["exclude_all_users"]

    blogs = wp(url = cfg["url"],
                username = cfg["username"],
                password = cfg["password"])
    
    data = d()
    
    log_file = cfg['log_file']
    logger = logging.getLogger(__name__)
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    fh = logging.FileHandler(log_file, mode='w')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    main(blogs)
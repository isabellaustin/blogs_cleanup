from wordpress import wp
from data import d
import json
import mysql.connector
import colorama
from colorama import Fore, Back
import logging
from tqdm.auto import tqdm
import os
import shutil

all_kept_users_unique: list[str] = []
all_del_users_unique: list[str] = []
all_other_del_unique: list[str] = []
user_dates: list[str] = []
blogs_dates: list[str] = []
nomads: list[int] = []

#tbd means to be deleted
sites_tbd: dict[str, int] = {}
users_tbd: dict[str, int] = {}
other_del_dict: dict[int, list[int]] = {} 
other_users_tbd: dict[str, int] = {}
deletion_dict: dict[str, list[int]] = {}
yearly_reg: dict[str, int] = {}
yearly_user_reg: dict[str, int] = {}
other_id_tbd = ()

def main(blogs) -> None:
    all_kept_sites = 0
    all_del_sites = 0

    """creates a file with a list of non-Butler users (i.e. users with emails that don't end in '@butler.edu')"""    
    outside_users: dict[int, str] = {}
    blogs.get_outside_users(outside_users, cnx)
    outside_data = outside_users.values()
    with open("outside_users.txt", "w") as f:
        for d in outside_data:
            if d not in exclude_outside_users:
                f.write("%s\n" % d)

    """creates a list of ids and usernames of blogs users"""    
    id_username: dict[int, str] = {}
    blogs.get_id_username(id_username, cnx)

    """creates a list of inactive users by finding the difference between the list of current users (created id_username list) 
        and all active users"""
    inactive_data = blogs.get_inactive_users(exclude = exclude_users, blogs_users=id_username.values())

    """creates a list of blogs in the database"""
    user_blogs: dict[int, str] = {}
    blogs.get_user_blogs(user_blogs, cnx)

    sites = list(user_blogs.keys())
    
    for site in sites:
        """gets the list of users on a site"""        
        
        site_users = blogs.get_site_users(site, cnx)

        remaining_users = len(site_users)
        site_path = user_blogs[site]
         
        for u in site_users: 
            username = id_username[u]

            if username in inactive_data:
                print(f"{Fore.RED}{username} will be removed from {site_path}{Fore.RESET}")
                remaining_users-=1

                if username in outside_data: #non-BU deleted
                    # a dict of the sites non-BU users are on
                    if site not in list(other_del_dict.keys()):
                        other_del_dict[site] = []
                    if u not in other_del_dict[site]:
                        other_del_dict[site].append(u) 

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

        index_num = int(list(sites).index(site)) + 1    #starts at 1 instead of 0
        print(f"SITE {index_num} OF {len(sites)}")

    data.sitestats_csv(id_username,outside_users,nomads,cnx) #needs to run for 'siteless users' stats
    # data.fetch_multisite_users(id_username, all_kept_users_unique,user_blogs,cnx)
    # data.remove_multisite_admins()
    # data.user_sitedata_csv(id_username,user_blogs,cnx)
    # data.userdata_csv(id_username,user_dates,yearly_user_reg,cnx)
    # data.sitedata_csv(id_username,user_blogs,blogs_dates,yearly_reg,cnx)
    # data.plugins_csv(cnx)
    # data.themes_csv(cnx)

    # deletion(outside_users,user_blogs,id_username,other_users_tbd)
    cnx.close()
    get_stats(inactive_data, outside_data, sites, all_kept_sites, all_del_sites, id_username)


def deletion(outside_users: dict[int, str], id_username: dict[int, str]) -> None:
    del_logger.setLevel(logging.INFO)
    """archiving blogs if they are abandoned, otherwise, deleting necessary users"""  
    #  site should already have zero users if its been put into the sites_tbd list

    # BU users on sites
    BU_sites = list(deletion_dict.keys())
    for site in tqdm(BU_sites):
        print(site) 
        user_list = deletion_dict[site]

        user_deletion(site, user_list,id_username)

        sites_tbd.pop(site)
        del deletion_dict[site]

    #non-BU users NOT on sites
    non_BU_ids = list(outside_users.keys())
    for id in tqdm(non_BU_ids):
        if id not in list(other_del_dict.keys()):
            username = id_username[id]

            blogs.network_del_user(id, del_logger)
            print(f"(Non-Butler){Fore.WHITE}{Back.RED} USER {username} was deleted from the network.{Back.RESET}{Fore.RESET}")


def user_deletion(site:str, user_list: list[int], id_username: dict[int, str]) -> None:
    del_logger.setLevel(logging.INFO)

    # add buwebservices (cfg["buwebservices_id"]) to site
    if buwebservices not in user_list:
        del_logger.info(f"buwebservices not in {site}'s user list")
        blogs.create_user(del_logger,buwebservices, site)

    del_blog = True
    user_id_tbd = list(users_tbd.values()) #BU users (6487)
    other_id_tbd = set([x for y in other_del_dict.values() for x in y]) #non-BU users; unique UIDs from the list of lists in other_del_dict.values() (198)

    for user_id in user_list:
        if user_id in user_id_tbd or user_id in other_id_tbd:
            username = id_username[user_id]
            if user_id in user_id_tbd:
                type = "Butler"
            else:
                type = "Non-Butler"

                if username in list(other_users_tbd.keys()):
                    del other_users_tbd[username]

                if username not in all_other_del_unique:
                    all_other_del_unique.append(username)

            blogs.reassign_user(user_id, buwebservices, del_logger)
            blogs.network_del_user(user_id, del_logger)
            
            print(f"({type}){Fore.WHITE}{Back.RED} USER {username} was deleted from the network.{Back.RESET}{Fore.RESET}")
        else:
            del_logger.info(f"ERROR: USER {username} NOT IN {site}'S USER LIST")
            del_blog = False
            
    if del_blog:
        if site in list(sites_tbd.keys()):
            blog_id = sites_tbd[site]

            # MAKE SITE SUBDIRECTORY
            export_dir = cfg['export_dir'] #backups is parent in this case
            directory = site[1:-1]

            path = os.path.join(export_dir, directory)
            os.mkdir(path)
            print("Directory '% s' created" % directory)
            
            # DOWNLOAD MEDIA
            blogs.export_site(site,path)
            blogs.get_attachments(site,path)

            # ZIP DIRECTORY AND MOVE TO 'BACKUPS'
            zip = shutil.make_archive(directory, 'zip', path)
            shutil.move(zip, export_dir)

            # DELETE SUBDIRECTORY AND SITE
            shutil.rmtree(path)
            blogs.delete_blog(blog_id, del_logger)
            
            print(f"{Fore.WHITE}{Back.RED}BLOG {site} was deleted.{Back.RESET}{Fore.RESET}")
    else:
        print(f"BLOG {site} will not be archived.")
        del_logger.info(f"BLOG {site} will not be archived.")


def get_stats(inactive:set[str], outside, sites: list[int], kept_sites: int, del_sites: int, id_username: dict[int, str]) -> None:
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
    total_del_users = len(all_del_users_unique) + len(nomads)
    logger.info(f"Number of deleted users: {total_del_users} ({len(all_del_users_unique)} Butler, {len(nomads)} non-Butler)\n")

    # REMAINING 
    logger.info(f"Number of remaining sites: {kept_sites}")
    total_kept_users = len(all_kept_users_unique) + (len(outside)-len(nomads))
    logger.info(f"Number of remaining users: {total_kept_users} ({len(all_kept_users_unique)} Butler, {(len(outside)-len(nomads))} non-Butler)\n") #other_users_tbd

    # STATISTICS
    perc_blog_cleanup = (del_sites / len(sites)) * 100
    perc_bformat = '{:.2f}'.format(perc_blog_cleanup)
    logger.info(f"Percent decrease in sites: {perc_bformat}%")

    perc_user_cleanup = (total_del_users / len(id_username)) * 100
    perc_uformat = '{:.2f}'.format(perc_user_cleanup)
    logger.info(f"Percent decrease in users: {perc_uformat}%")


if __name__ == "__main__":
    colorama.init()
    
    with open('config.json', 'r') as f:
        cfg=json.load(f)
        exclude_users = cfg["exclude_users"]
        exclude_outside_users = cfg["exclude_outside_users"]
        exclude_all_users = cfg["exclude_all_users"]
    
    cnx = mysql.connector.connect(user=cfg["db_username"], password=cfg["db_password"], host="docker-dev.butler.edu", database="wp_blogs_dev")

    blogs = wp(url = cfg["url"],
                username = cfg["username"],
                password = cfg["password"])
    
    data = d()

    formatter = logging.Formatter('%(asctime)s - %(message)s')

    # statistics
    log_file = cfg['log_file']
    logger = logging.getLogger("log1")
    fh = logging.FileHandler(log_file, mode='w')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    # deletion
    del_log_file = cfg['del_log_file']
    del_logger = logging.getLogger("log2")
    fh2 = logging.FileHandler(del_log_file, mode='w')
    fh2.setFormatter(formatter)
    del_logger.addHandler(fh2)
    
    ''' MAKE 'BACKUPS' DIRECTORY
    parent_dir = cfg['parent_dir']
    directory = "backups"

    path = os.path.join(parent_dir, directory)
    os.mkdir(path) #0o666 allows read and write file operations
    print("Directory '% s' created" % directory) 
    '''
    buwebservices = cfg["buwebservices_id"]

    main(blogs)
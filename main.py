from wordpress import wp
import json
import mysql.connector

import colorama
from colorama import Fore, Back
from tqdm.auto import tqdm

import logging
import csv
import collections
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

"""stat variables"""
all_kept_users = []
all_kept_users_unique = []
all_del_users = []
all_del_users_unique = []
all_other_del = []
all_other_del_unique = []
dates = []
nomads = [] #list of users without any sites
key = []

#tbd: to be deleted
sites_tbd = {}
users_tbd = {}
other_users_tbd = {}
yearly_reg = {}
#==========================================

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

    """creates a list of inactive users by finding the difference between the list of current users (created id_username list) 
        and all active users"""
    inactive_data = blogs.get_inactive_users(exclude = exclude_all_users, blogs_users=id_username.values())

    """creates a list of blogs in the database"""
    user_blogs = {}

    blogs.get_user_blogs(user_blogs, cnx)
    sites = list(user_blogs.keys()) #gets site id

    # for site in sites:
    #     """gets the list of users on a site"""        
    #     site_users = blogs.get_site_users(site, cnx)
    #     remaining_users = len(site_users)
    #     site_path = user_blogs[site]
         
    #     for u in site_users: 
    #         username = id_username[u] # key: id, value: username

    #         if username in inactive_data: #if user is inactive
    #             print(f"{Fore.RED}{username} will be removed from {site_path}{Fore.RESET}")

    #             remaining_users-=1

    #             if username in outside_data: #non-BU deleted
    #                 other_users_tbd[username] = u # key: username, value: id

    #                 all_other_del.append(username)
    #                 if username not in all_other_del_unique: 
    #                     all_other_del_unique.append(username)
    #             else:                       #BU deleted
    #                 users_tbd[username] = u # key: username, value: id

    #                 all_del_users.append(username)
    #                 if username not in all_del_users_unique: 
    #                     all_del_users_unique.append(username) 
    #         else:
    #             print(f"{Fore.GREEN}{username} will not be removed from {site_path}{Fore.RESET}")

    #             all_kept_users.append(username)
    #             if username not in all_kept_users_unique: 
    #                 all_kept_users_unique.append(username)

    #     if remaining_users == 0:
    #         print(f"{Fore.WHITE}{Back.RED}{site_path} has no remaining users and will be archived{Back.RESET}")

    #         all_del_sites+=1
    #         sites_tbd[site_path] = site # key: path, value: id
    #     else:
    #         all_kept_sites+=1

    #     index_num = int(list(sites).index(site)) + 1    #starts at 1 instead of 0
    #     print(f"SITE {index_num} OF {len(sites)}")

    id_list = list(id_username.keys())
    username_list = list(id_username.values())

    #==========================================
    fetch_multisite_users(id_username)
    user_csv(username_list,id_list,user_blogs)
    site_csv(username_list,id_list,user_blogs)
    remove_multisite_admins()

    blog_deletion()
    user_deletion(outside_users)

    cnx.close()

    # get_stats(inactive_data, outside_data, sites, all_kept_sites, all_del_sites, id_username)


# DELETION ========================================================================================
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
            other_users_tbd.pop(ou)

        print(f"(Non-Butler){Fore.WHITE}{Back.RED} USER {ou} was deleted from the database.{Back.RESET}{Fore.RESET}")

    # print(other_users_tbd)
    # print(len(other_users_tbd))

    # print(len(all_del_users_unique))
    # print(len(all_other_del_unique))


# DATA ============================================================================================
def fetch_multisite_users(id_username) -> None:  
    """Gets the email for users that are on 15 or more sites and the amount of sites they're on

    Args:
        id_username (dict): dict of id and usernames
    """     
    
    header = ['user_email', 'num_of_sites'] 
    with open('multisite_users.csv', 'w', encoding='UTF8') as f:
        writer = csv.writer(f)
        writer.writerow(header)

        print("Fetching multisite users...")
        id_list = list(id_username.keys())
        username_list = list(id_username.values())
        for user in tqdm(list(all_kept_users_unique)):
            index = username_list.index(f"{user}")
            id = id_list[index]

            user_site_ids, user_sites = blogs.get_user_sites(id,cnx)
            
            if len(user_sites) >= 15:
                data = [f'{user}', f'{len(user_sites)}']
                writer.writerow(data)


def user_csv(username_list, id_list, user_blogs) -> None:
    """Lists the site_id and slug for each site a user is on

    Args:
        username_list (list): list of just usernames from id_username dict
        id_list (list): list of just user ids from id_username dict
        user_blogs (list): list of blogs in the database
    """    
    
    header = ["user_id", "user_email", "site_id", "slug"] 
    with open('userdata.csv', 'w', encoding='UTF8') as f:
        writer = csv.writer(f)
        writer.writerow(header)

        print("Fetching users' site information...")
        for user in tqdm(username_list):
            index = username_list.index(f"{user}")
            id = id_list[index] #user_id

            user_site_ids, user_site_roles = blogs.get_user_sites(id,cnx)
            for blog_id in user_site_ids:
                try:
                    path = user_blogs[blog_id]
                except KeyError as ke:
                    key.append(blog_id) #37
                    continue

                data = [f'{id}', f'{user}', f'{blog_id}', f'{path}']
                writer.writerow(data)

    # sitestats.csv
    sites_count = collections.Counter()
    header = ['user_email', 'num_of_sites'] 
    with open('sitestats.csv', 'w', encoding='UTF8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        with open('userdata.csv') as input_file:
            for user in username_list:
                for row in csv.reader(input_file, delimiter=','):
                    sites_count[row[1]] += 1

                # if sites_count[user] > 0: #8205
                data = [f'{user}',f'{sites_count[user]}']
                writer.writerow(data)


def site_csv(username_list, id_list, user_blogs) -> None:
    """Gets blog_id, slug, registered, and last_updated for every site

    Args:
        username_list (list): list of just usernames from id_username dict
        id_list (list): list of just user ids from id_username dict
        user_blogs (list): list of blogs in the database
    """    
    
    header = ["blog_id", "slug", "registered", "last_updated"]
    with open('sitedata.csv', 'w', encoding='UTF8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        
        print("Fetching site details...")
        for user in tqdm(username_list):
            index = username_list.index(f"{user}")
            user_id = id_list[index]
        
            user_site_ids, user_site_roles = blogs.get_user_sites(user_id,cnx)
        
            for blog_id in user_site_ids:
                try:
                    slug = user_blogs[blog_id]
                except KeyError as ke:
                    key.append(blog_id) #37
                    continue
                
                try:
                    year_month, last_updated = blogs.get_site_info(blog_id,cnx)
                except ValueError as ve:
                    pass
                
                if year_month not in dates:
                    dates.append(year_month) 
                    regs = blogs.get_year_regs(year_month,cnx)
                    # print(year, regs)
                    yearly_reg[year_month] = regs

                data = [f'{blog_id}', f'{slug}', f'{year_month}', f'{last_updated}']
                writer.writerow(data)

    date_list = list(yearly_reg.keys())
    ordered_dates = sorted(date_list)
    new_dates = [x[:-1] for x in ordered_dates] #remove the '%' from the x-axis values

    sums = []
    total = 0
    for r in list(yearly_reg.values()):
        total += r
        sums.append(total)
    log_sum = [(i//10) for i in sums]

    # YEARLY_REG
    # plt.rcParams["figure.figsize"] = [23.50, 15.50]
    # plt.rcParams["figure.autolayout"] = True
    
    # plt.plot(new_dates[:-1], list(yearly_reg.values())[:-1], label='month-year registrations') #[:-1] removes 'None' value from Graph; "None" is from the admin site's reg date
    # plt.plot(new_dates[:-1], log_sum[:-1], label='cumulative registrations (values % 10)')
    # plt.xticks(rotation = 90)
    # plt.yticks(np.arange(min(yearly_reg.values()), max(sums), 50))

    # plt.title("Blog Registration by Date")
    # plt.xlabel("Date (yyyy-mm)")
    # plt.ylabel("Number of Blogs Registered")
    # plt.margins(x=0.01, y=0.01)

    # plt.legend(prop={'size': 15},borderpad=2)
    # # plt.legend(loc="upper left")

    # plt.show(block=True)
    # plt.savefig('yearly_reg.png')
        
    # QUARTERLY_REG 
    q_key = (new_dates[:-1])
    quarterly_keys = []
    for i in range(0,len(q_key),4):
        qik = q_key[i]
        quarterly_keys.append(qik)

    q_val = (list(yearly_reg.values())[:-1])
    quarterly_values = []
    for i in range(0,len(q_val),4):
        qiv = sum(q_val[i:(i+3)])
        quarterly_values.append(qiv)
    
    df = pd.DataFrame({'date': quarterly_keys,'registrations': quarterly_values})
    df['quarter'] = pd.PeriodIndex(df['date'], freq='Q')
    quarters = [str(x) for x in list((df['quarter']))] #need to convert PeriodIndex to string
    # print(df)
    
    # plt.rcParams["figure.figsize"] = [10.50, 7.50]
    # plt.rcParams["figure.autolayout"] = True

    # plt.plot(quarters, df['registrations'])
    # plt.xticks(rotation = 90)
    # plt.yticks(np.arange(min(quarterly_values)-2, max(quarterly_values), 50))

    # plt.title("Quarterly Blog Registrations")
    # plt.xlabel("Quarter")
    # plt.ylabel("Number of Blogs Registered")
    # plt.margins(x=0.01, y=0.01)

    # plt.show(block=True)
    # plt.savefig('quarterly_reg.png')


def remove_multisite_admins() -> None:
    multisite_user = []
    multisite_site = []
    user_sites = {}
    sites = []
    user_indices = {}
    index = []
    indices_count = collections.Counter()
    
    with open('multisite_users.csv') as f:
        for row in csv.reader(f, delimiter=','):
            multisite_user.append(row[0])

    with open('userdata.csv') as input_file:
        sites.clear()
        for row in csv.reader(input_file, delimiter=','):
            # sites.clear()
            # sites = []
            for user in multisite_user[1:]:
                if user == row[1]:
                    indices_count[user] += 1
                    sites.append(int(row[2]))
                    user_indices[int(row[2])] = row[1]
           
        # print(indices_count.keys())
        # print(indices_count.values())
        print(user_indices)

        blog_ids = list(user_indices.keys()) #blog_ids
        user_emails = list(user_indices.values()) #user_emails
        # for id in blog_ids:
        #     if id != 1:
                # delete user_email from id
        #admin blog_id: 1


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
    
    log_file = cfg['log_file']
    logger = logging.getLogger(__name__)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh = logging.FileHandler(log_file, mode='w')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    main(blogs)
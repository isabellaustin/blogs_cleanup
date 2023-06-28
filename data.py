from wordpress import wp
import json
from phpserialize import *

from tqdm.auto import tqdm
import csv
import collections

class d:
    def __init__(self) -> None:
        with open('config.json', 'r') as f:
            cfg=json.load(f) 
       
        self.wp = wp(url = cfg["url"],
                username = cfg["username"],
                password = cfg["password"])

       
    def fetch_multisite_users(self,username_list,id_list,all_kept_users_unique,user_blogs,cnx) -> None:  
        """Gets the email for users that are on 15 or more sites and the amount of sites they're on

        Args:
            id_username (dict): dict of id and usernames
        """  

        user_site_ids = {}

        header = ['user_email', 'num_of_sites'] 
        with open('multisite_users.csv', 'w', encoding='UTF8') as f:
            writer = csv.writer(f)
            writer.writerow(header)

            print("Fetching multisite users...")
            for user in tqdm(list(all_kept_users_unique)):
                index = username_list.index(f"{user}")
                id = id_list[index]

                user_site_ids, user_roles = self.wp.get_user_sites(id,cnx)

                if len(user_site_ids[id]) >= 15:
                    data = [f'{user}', f'{len(user_site_ids[id])}']
                    writer.writerow(data)


    def remove_multisite_admins(self) -> None:
        multisite_user = []
        user_indices = {}
        
        with open('multisite_users.csv') as f:
            for row in csv.reader(f, delimiter=','):
                multisite_user.append(row[0])
                user_indices[row[0]] = []

        with open('user_sitedata.csv') as input_file:
            for row in csv.reader(input_file, delimiter=','):

                if row[1] in user_indices.keys():
                    user_indices[row[1]].append(row[3])

            with open('multisite_removals.csv', 'w', encoding='UTF8') as f:
                writer = csv.writer(f)
                user_emails = list(user_indices.keys())
                for email in user_emails:
                    blog_paths = list(user_indices[email])
                    for path in blog_paths:
                        # self.wp.remove_role(email,path)
                        data = [f"{email} was removed from {path}."]
                        writer.writerow(data)


    def user_sitedata_csv(self,username_list,id_list,user_blogs,key,cnx) -> None:
        """Lists the site_id and slug for each site a user is on

        Args:
            username_list (list): list of just usernames from id_username dict
            id_list (list): list of just user ids from id_username dict
            user_blogs (list): list of blogs in the database
        """    
        
        header = ["user_id", "user_email", "site_id", "slug"] 
        with open('user_sitedata.csv', 'w', encoding='UTF8') as f:
            writer = csv.writer(f)
            writer.writerow(header)

            print("Fetching users' site information...")
            for user in tqdm(username_list):
                index = username_list.index(f"{user}")
                id = id_list[index] #user_id

                user_site_ids, user_roles = self.wp.get_user_sites(id,cnx)
                for blog_id in user_site_ids:
                    try:
                        path = user_blogs[blog_id]
                    except KeyError as ke:
                        key.append(blog_id) #37
                        continue

                    data = [f'{id}', f'{user}', f'{blog_id}', f'{path}']
                    writer.writerow(data)


    def userdata_csv(self,username_list,id_list,user_dates,yearly_user_reg,cnx) -> None:
        header = ["user_id", "user_email", "user_registered"] 
        with open('userdata.csv', 'w', encoding='UTF8') as f:
            writer = csv.writer(f)
            writer.writerow(header)

            print("Fetching user information...")
            for user in username_list:
                index = username_list.index(f"{user}")
                id = id_list[index] #user_id

                user_reg_date = self.wp.get_user_info(id,cnx)

                if user_reg_date not in user_dates:
                        user_dates.append(user_reg_date) 
                        regs = self.wp.get_user_regs(user_reg_date,cnx)
                        # print(year, regs)
                        yearly_user_reg[user_reg_date] = regs

                data = [f'{id}', f'{user}', f'{user_reg_date}']
                writer.writerow(data)
        
        date_list = list(yearly_user_reg.keys())
        ordered_dates = sorted(date_list)
        new_dates = [x[:-1] for x in ordered_dates]

        wp.yearly_user_reg(yearly_user_reg, new_dates)


    def sitestats_csv(self,username_list,id_list,outside_users,all_other_del_unique,nomads,cnx) -> None:
        print("Fetching siteless users...")
        for id in tqdm(list(outside_users.keys())):
            user_site_ids, user_roles = self.wp.get_user_sites(id,cnx)
        
            if len(user_roles) == 0:
                nomads.append(id)

        sites_count = collections.Counter()
        header = ['user_email', 'num_of_sites'] 
        with open('sitestats.csv', 'w', encoding='UTF8') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            with open('user_sitedata.csv') as input_file:

                print("Fetching site stats...")
                for user in tqdm(username_list):
                    for row in csv.reader(input_file, delimiter=','):
                        sites_count[row[1]] += 1

                    # if sites_count[user] > 0: #8205
                    data = [f'{user}',f'{sites_count[user]}']
                    writer.writerow(data)


    def sitedata_csv(self,username_list, id_list, user_blogs,blogs_dates,yearly_reg,key,cnx) -> None:
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
            # print(len(username_list))
            print("Fetching site information...")
            for user in tqdm(username_list):
                
                index = username_list.index(f"{user}")
                user_id = id_list[index]
            
                user_site_ids, user_roles = self.wp.get_user_sites(user_id,cnx)
            
                for blog_id in user_site_ids:
                    try:
                        slug = user_blogs[blog_id]
                    except KeyError as ke:
                        key.append(blog_id) #37
                        continue
                    
                    try:
                        year_month, last_updated = self.wp.get_site_info(blog_id,cnx)
                    except ValueError as ve:
                        pass
                    
                    if year_month not in blogs_dates:
                        blogs_dates.append(year_month) 
                        regs = self.wp.get_blogs_regs(year_month,cnx)
                        yearly_reg[year_month] = regs

                    data = [f'{blog_id}', f'{slug}', f'{year_month}', f'{last_updated}']
                    writer.writerow(data)

            # df = pd.read_csv('sitedata.csv')
            # df.drop_duplicates(inplace=True)
            # df.to_csv('sitedata.csv', index=False)

        date_list = list(yearly_reg.keys())

        ordered_dates = sorted(date_list)
        new_dates = [x[:-1] for x in ordered_dates] #remove the '%' from the x-axis values

        wp.yearly_blog_reg(yearly_reg, new_dates)
        wp.quarterly_blog_reg(yearly_reg, new_dates)


    def plugins_csv(self,cnx) -> None:
        plugin_count = collections.Counter()
        unique_plugins = []
        sites = {}
        site_plugins = {} 

        with open('sitedata.csv') as f:
            for row in csv.reader(f, delimiter=','):
                sites[row[1]] = (row[0])
                site_plugins[row[1]] = []

        print("Fetching plugin stats...")
        for site in tqdm(list(sites.keys())[1:]):
            id = sites[site]
            blog_id = int(id)

            plugins = self.wp.get_site_plugins(blog_id,cnx)

            if site in site_plugins.keys():
                site_plugins[site] = plugins
            
            for p in site_plugins[site]:
                if p not in unique_plugins:
                    unique_plugins.append(p)
                plugin_count[p] += 1

        d.pluginstats_csv(self,sites,site_plugins,unique_plugins,plugin_count,cnx)
            

    def pluginstats_csv(self,sites,site_plugins,unique_plugins,plugin_count,cnx) -> None:
        all_plugins = open("plugins.txt").read().splitlines()
        active1, active6, active21, active101, active501 = [], [], [], [], []

        headerS = ["plugin", "plugin_activations"]
        with open('pluginstats.csv', 'w', encoding='UTF8') as input_file: 
            writer = csv.writer(input_file)
            writer.writerow(headerS)

            for plug in unique_plugins:
                activations = plugin_count[plug]

                dataS = [f'{plug}', f'{plugin_count[plug]}']
                writer = csv.writer(input_file)
                writer.writerow(dataS)

                try:
                    p = plug.split("/")[0]
                    all_plugins.remove(p)
                except ValueError as ve:
                    pass
                inactive = all_plugins

                if activations <=5:
                    active1.append(plug)
                elif activations <=20:
                    active6.append(plug)
                elif activations <=100:
                    active21.append(plug)
                elif activations <=500:
                    active101.append(plug)
                elif activations >=501:
                    active501.append(plug)

        x_values = ["1-5", "6-20", "21-100", "101-500", "501+"]
        y_values = [len(active1), len(active6), len(active21), len(active101), len(active501)]
        wp.plugin_activation(x_values, y_values)

        d.plugindata_csv(self,sites,site_plugins,inactive,cnx)
            

    def plugindata_csv(self,sites,site_plugins,inactive,cnx) -> None:       
        header = ["inactive_plugin"]
        with open('inactive_plugins.csv', 'w', encoding='UTF8') as input_file: 
            writer = csv.writer(input_file)
            writer.writerow(header)
                    
            print("Fetching inactive plugins...")
            for i in tqdm(inactive):
                data = [f'{i}']
                writer.writerow(data)

        headerD = ["site_id", "slug", "plugin_count", "plugins"]
        with open('plugindata.csv', 'w', encoding='UTF8') as input_file: 
            writer = csv.writer(input_file)
            writer.writerow(headerD)
                    
            print("Fetching plugin information...")
            for site in tqdm(list(sites.keys())[1:]):
                id = sites[site]
                blog_id = int(id)

                plugins = self.wp.get_site_plugins(blog_id,cnx)

                if site in site_plugins.keys():
                    site_plugins[site] = plugins

                dataD = [f'{id}', f'{site}', f'{len(site_plugins[site])}', f'{site_plugins[site]}']
                writer.writerow(dataD)


    def themes_csv(self,cnx) -> None:
        sites_dict = {}
        themes_dict = {} 
        theme_count = collections.Counter()
        unique_themes = []

        with open('sitedata.csv') as f:
            for row in csv.reader(f, delimiter=','):
                sites_dict[row[1]] = (row[0])
                themes_dict[row[1]] = []

        d.themestats_csv(self,sites_dict, themes_dict, theme_count, unique_themes,cnx)

        headerD = ["site_id", "slug", "template_count", "site_templates"]
        with open('themedata.csv', 'w', encoding='UTF8') as input_file: 
            writer = csv.writer(input_file)
            writer.writerow(headerD)
                    
            print("Fetching theme information...")
            for site in tqdm(list(sites_dict.keys())[1:]):
                id = sites_dict[site]
                blog_id = int(id)

                themes = self.wp.get_site_themes(blog_id,cnx)

                if site in themes_dict.keys():
                    themes_dict[site] = themes

                dataD = [f'{id}', f'{site}', f'{len(themes_dict[site])}', f'{themes_dict[site]}']
                writer.writerow(dataD)


    def themestats_csv(self,sites_dict, themes_dict, theme_count, unique_themes,cnx) -> None:
        headerS = ["theme", "theme_activations"]
        with open('themestats.csv', 'w', encoding='UTF8') as input_file: 
            writer = csv.writer(input_file)
            writer.writerow(headerS)
                    
            print("Fetching theme stats...")
            for site in tqdm(list(sites_dict.keys())[1:]):
                id = sites_dict[site]
                blog_id = int(id)

                themes = self.wp.get_site_themes(blog_id,cnx)

                if site in themes_dict.keys():
                    themes_dict[site] = themes
                
                for p in themes_dict[site]:
                    if p not in unique_themes:
                        unique_themes.append(p)
                    theme_count[p] += 1
                    
            for plug in unique_themes:
                dataS = [f'{plug}', f'{theme_count[plug]}']
                writer.writerow(dataS)

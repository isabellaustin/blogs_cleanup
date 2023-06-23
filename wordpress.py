import requests
import subprocess
from phpserialize import *
import base64

from typing import List
from colorama import Fore, Back
from phpserialize import *

import csv
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

class wp:
# INITALIZATION ===================================================================================
    def __init__(self, url: str = "https://localhost", username: str = "", password: str = "") -> None:
        self.url = url
        self.api_url = f"{self.url}/wp-json/wp/v2/"
        self.username = username
        self.password = password
        self.make_cred()
        self.headers = {'Authorization': f'Basic {self.token}', 'connection': 'close'}
        self.session = requests.Session()

    def __str__(self) -> str:
        return f"<wp({self.url})>"


    def make_cred(self) -> None:
        credentials = self.username + ":" + self.password
        self.token = base64.b64encode(credentials.encode()).decode('utf-8')


# DELETION ========================================================================================
    def create_user(self, username: str = "") -> dict:
        """adds a user to a blog

        Args:
            username (str, optional): _description_. Defaults to "".

        Returns:
            dict: _description_
        """          
        response = self.session.post(f"{self.api_url}users", headers = self.headers)
        if response.status_code != 200:
            return response.json()


    def get_id_by_email(self, user_key, mysql) -> int: # user_key = username/first part of email
        """Returns the id of users with non-Butler emails

        Args:
            user_key (str): user email
            mysql (connector): SQL connection

        Returns:
            str: id for a non-Butler user
        """ 
        cursor = mysql.cursor()

        query = (f'''select id from wp_users where user_email like "{user_key}%"''')
        cursor.execute(query)

        results = cursor.fetchone()
        # if results is None:
        #     return -1
        id = int(results[0]) 
        
        cursor.close()

        return id
  

    def reassign_user(self, user_id, new_id) -> None:
        """deletes user {user_id} and reassigns their posts to declared user {new_id}

        Args:
            user_id (int): unique id number
            new_id (int): the id that the soon-to-be-deleted user's content will be transfered to
        """        
        p = subprocess.run(f"wp user delete {user_id} --reassign={new_id}", shell=True, capture_output=True)
        # print(p.stdout)


    def network_del_user(self, user_id) -> None:
        """delete the user from the entire network

        Args:
            user_id (int): unique id number
        """        
        subprocess.run(f"wp user delete {user_id} --network", shell=True, capture_output=True)


    def archive_blog(self, blog_id) -> None:
        """archive a blog

        Args:
            blog_id (int): unique id number
        """        
        subprocess.run(f"wp site archive {blog_id}", shell=True, capture_output=True)

    
    def delete_blog(self, blog_id) -> None:
        """delete a blog

        Args:
            blog_id (int): unique id number
        """        
        subprocess.run(f"wp site delete {blog_id}", shell=True, capture_output=True)


# DELETION ========================================================================================
    def remove_role(self, user_email, blog_path) -> None:
        subprocess.run(f"wp user remove-role {user_email} administrator --url=https://blogs-dev.butler.edu{blog_path}", shell=True, capture_output=True)


# OUTSIDE_USERS LIST ============================================================================== 
    def get_outside_users(self, outside_users, mysql) -> None:
        """Gets the id, username, and registration date of blogs users with non-Butler emails.

        Args:
            outside_users (dict): empty dict that is to-be appended in this function
            mysql (connector): SQL connection
        """        
        cursor = mysql.cursor()
        
        query = ('''select id, user_email, DATE_FORMAT(user_registered,'reg-date: %m-%d-%Y')
                    from wp_users 
                    where user_email not like "%@butler.edu"''') #strp time
        cursor.execute(query)

        for(id, user_email, user_registered) in cursor:
            outside_users [id, user_registered] = user_email
            # outside_users[int(id)] = {"registered": user_registered, "email": user_email.split('@')[0]}

        cursor.close()


# INACTIVE_DATA LIST ==============================================================================  
    def get_inactive_users(self, exclude: list[str] = [], blogs_users: list[str] = []) -> List[str]:
        """Finds the difference between the list of current users and all active users 
            (all_users.txt) on blogs.butler.edu

        Args:
            exclude (list[str], optional): users to be ignored. Defaults to [].
            blogs_users (list[str], optional): id_username list. Defaults to [].

        Returns:
            List[str]: a list of inactive users
        """
        all_users = set(f"{line.strip().lower()}@butler.edu" for line in open('all_users.txt')
                        if line.strip() not in exclude)
        difference = set(blogs_users).difference(all_users)

        return difference


# SITE_USERS LIST =================================================================================  
    def get_site_users(self, site_id, mysql) -> List[str]: 
        """Gets the users for a specific site.

        Args:
            site_id (int): unique id number
            mysql (connector): SQL connection

        Returns:
            List[str]: list of site users
        """            
        cursor = mysql.cursor()
        query = ('''select * from wp_users 
                    u join wp_usermeta um on u.id=um.user_id 
                    where um.meta_key="wp_%s_capabilities"''')
        cursor.execute(query, (site_id,))

        results = cursor.fetchall()

        skip_users = [9197309, 9192475] #buwebservices, teststudent
        users = [int(r[0]) for r in results if int(r[0]) not in skip_users]

        cursor.close()

        return users

          
# ID_USERNAME LIST ================================================================================
    def get_id_username(self, id_username, mysql) -> None: 
        """Gets the id and username of blogs users with Butler emails.

        Args:
            id_username (dict): empty dict that is to-be appended in this function
            mysql (connector): SQL connection
        """        
        cursor = mysql.cursor()
        
        query = ('''select id, user_email from wp_users''')
        cursor.execute(query)

        for(id, user_email) in cursor:
            id_username [id] = user_email

        cursor.close()


# USER_BLOGS LIST =================================================================================
    def get_user_blogs(self, user_blogs, mysql) -> None: 
        """Gets all the blog ids and blog paths.

        Args:
            user_blogs (dict): empty dict that is to-be appended in this function
            mysql (connector): SQL connection
        """        
        cursor = mysql.cursor()

        query = ('''select blog_id, path from wp_blogs''')
        cursor.execute(query)

        for(blog_id, path) in cursor:
            user_blogs [blog_id] = path
        
        cursor.close()


# DATA ============================================================================================
    def get_user_sites(self,user_id:int,mysql) -> list[str]:
        """Returns a list of sites that a specific user is on

        Args:
            user_id (int): unique user id number
            mysql (connector): SQL connection

        Returns:
            list[str]: list of sites a specific user is on
        """        
        cursor = mysql.cursor()
        
        query = ('select * from wp_usermeta where user_id = %s and meta_key like "%capabilities"')
        # and meta_value like '%administrator'
        cursor.execute(query, (user_id,))

        results = cursor.fetchall()
        sites = []
        site_ids = []

        for r in results:
            try:
                site_ids.append(int(r[2].split("_")[1]))
            except ValueError as ve:
                continue
            
            sites.append(r[3].split("_")[0])

        cursor.close()

        return site_ids, sites


    def get_site_plugins(self,blog_id:int,mysql) -> list[str]:
        cursor = mysql.cursor()
        
        query = ('select option_value from wp_%s_options where option_name = "active_plugins"')
        cursor.execute(query, (blog_id,))

        results = cursor.fetchall()
        plugins = []

        for r in results:
            data = r[0]
            plugin_dict = loads(data.encode())
            for p in plugin_dict.keys():
                plugin = plugin_dict[p].decode()
                plugins.append(plugin) #[0])
            

        cursor.close()

        return plugins
    

    def get_site_themes(self,blog_id:int,mysql) -> list[str]:
        cursor = mysql.cursor()

        # key = str(blog_id)
        query = ('select option_value from wp_%s_options where option_name = "template"')
        cursor.execute(query, (blog_id,))

        results = cursor.fetchall()
        themes = []

        for r in results:
            themes.append(r[0])

        cursor.close()

        return themes


    def get_site_info(self,blog_id:int,mysql) -> str:
        """Returns the date a blog was registered and last updated as strings

        Args:
            blog_id (int): unique site id number
            mysql (connector): SQL connection

        Returns:
            str: date (mm-yyyy) as a string and date of the blogs last update
        """            
        cursor = mysql.cursor()
        
        query = ('''select registered, last_updated from wp_blogs where blog_id = %s''')
                    # and meta_value like '%administrator'
        cursor.execute(query, (blog_id,))

        results = cursor.fetchall()
        reg_dates = ""
        updates = ""

        for r in results:
            reg_dates = str(r[0]).split(" ")[0] 
            year_month = (f"{reg_dates[:7]}%")         
            updates = str(r[1]).split(" ")[0]

        cursor.close()

        return str(year_month), updates
    

    def get_user_info(self,user_id:int,mysql) -> str:
        """Returns the date a blog was registered and last updated as strings

        Args:
            user_id (int): user_id (int): unique user id number
            mysql (connector): SQL connection

        Returns:
            str: date (mm-yyyy) as a string and date of the blogs last update
        """            
        cursor = mysql.cursor()
        
        query = ('''select user_registered from wp_users where ID = %s''')
        cursor.execute(query, (user_id,))

        results = cursor.fetchall()
        reg_dates = ""

        for r in results:
            reg_dates = str(r[0]).split(" ")[0] 
            year_month = (f"{reg_dates[:7]}%")

        cursor.close()

        return str(year_month)
    

    def get_blogs_regs(self,date,mysql) -> int:
        """Returns the number of blogs created for a specific date (mm-yyyy)

        Args:
            user_id (int): user_id (int): unique user id number
            mysql (connector): SQL connection

        Returns:
            int: number of sites registered
        """            
        cursor = mysql.cursor()
        
        query = ('''select distinct count(*) from wp_blogs where date(registered) like %s''')
        # select count(*) from wp_blogs where date(registered) like
        # and meta_value like '%administrator'
        cursor.execute(query, (date,))

        results = cursor.fetchall()
        sites = 0

        for r in results:
            sites = int(r[0])

        cursor.close()

        return sites
    

    def get_user_regs(self,date,mysql) -> int:         
        cursor = mysql.cursor()
        
        query = ('''select distinct count(*) from wp_users where date(user_registered) like %s''')
        # select count(*) from wp_blogs where date(registered) like
        # and meta_value like '%administrator'
        cursor.execute(query, (date,))

        results = cursor.fetchall()
        sites = 0

        for r in results:
            sites = int(r[0])

        cursor.close()

        return sites

# ====================
    def yearly_blog_reg(yearly_reg, new_dates) -> None:
        # creates cumulative reg values
        sums = []
        total = 0
        for r in list(yearly_reg.values()):
            total += r
            sums.append(total)
        log_sum = [(i//10) for i in sums]

        plt.rcParams["figure.figsize"] = [23.50, 15.50]
        plt.rcParams["figure.autolayout"] = True
        
        plt.plot(new_dates[:-1], list(yearly_reg.values())[:-1], label='month-year registrations') #[:-1] removes 'None' value from Graph; "None" is from the admin site's reg date
        plt.plot(new_dates[:-1], log_sum[:-1], label='cumulative registrations (values % 10)')
        plt.xticks(rotation = 90)
        plt.yticks(np.arange(min(yearly_reg.values()), max(sums), 50))

        plt.title("Blog Registration by Date")
        plt.xlabel("Date (yyyy-mm)")
        plt.ylabel("Number of Blogs Registered")
        plt.margins(x=0.01, y=0.01)

        plt.legend(prop={'size': 15},borderpad=2)
        # plt.legend(loc="upper left")

        plt.show(block=True)
        plt.savefig('yearly_blog_reg.png')


    def quarterly_blog_reg(yearly_reg, new_dates) -> None:
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
        
        plt.rcParams["figure.figsize"] = [10.50, 7.50]
        plt.rcParams["figure.autolayout"] = True

        plt.plot(quarters, df['registrations'])
        plt.xticks(rotation = 90)
        plt.yticks(np.arange(min(quarterly_values)-2, max(quarterly_values), 50))

        plt.title("Quarterly Blog Registrations")
        plt.xlabel("Quarter")
        plt.ylabel("Number of Blogs Registered")
        plt.margins(x=0.01, y=0.01)

        plt.show(block=True)
        plt.savefig('quarterly_blog_reg.png')


    def yearly_user_reg(yearly_reg, new_dates) -> None:
        # creates cumulative reg values
        sums = []
        total = 0
        for r in list(yearly_reg.values()):
            total += r
            sums.append(total)
        log_sum = [(i//10) for i in sums]

        plt.rcParams["figure.figsize"] = [23.50, 15.50]
        plt.rcParams["figure.autolayout"] = True
        
        plt.plot(new_dates[:-1], list(yearly_reg.values())[:-1], label='month-year registrations') #[:-1] removes 'None' value from Graph; "None" is from the admin site's reg date
        plt.plot(new_dates[:-1], log_sum[:-1], label='cumulative registrations (values % 10)')
        plt.xticks(rotation = 90)
        plt.yticks(np.arange(min(yearly_reg.values())-1, max(sums), 50))

        plt.title("User Registration by Date")
        plt.xlabel("Date (yyyy-mm)")
        plt.ylabel("Number of Users Registered")
        plt.margins(x=0.01, y=0.01)

        plt.legend(prop={'size': 15},borderpad=2)
        # plt.legend(loc="upper left")

        plt.show(block=True)
        plt.savefig('yearly_user_reg.png')


    def remove_multisite_admins() -> None:
        multisite_user = []
        user_indices = {}
        # indices_count = collections.Counter()
        
        with open('multisite_users.csv') as f:
            for row in csv.reader(f, delimiter=','):
                multisite_user.append(row[0])
                user_indices[row[0]] = []

        with open('user_sitedata.csv') as input_file:
            for row in csv.reader(input_file, delimiter=','):

                if row[1] in user_indices.keys():
                    user_indices[row[1]].append(row[3])

            user_emails = list(user_indices.keys())
            for email in user_emails:
                blog_paths = list(user_indices[email])
                for path in blog_paths:
                    # what if it is there own site? (ex. bquincy@butler.edu is admin on /bquincy/)

                    # wp.remove_role(email,path)
                    print(f"{Fore.WHITE}{Back.RED} ADMIN {email} was removed from {path}.{Back.RESET}{Fore.RESET}")

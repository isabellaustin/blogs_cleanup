import requests
import subprocess
import base64
from typing import List

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
        
        query = ('''select * from wp_usermeta where user_id = %s and meta_key like "%capabilities"''')
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


    def get_site_info(self,user_id:int,mysql) -> str:
        """Returns the date a blog was registered and last updated as strings

        Args:
            user_id (int): user_id (int): unique user id number
            mysql (connector): SQL connection

        Returns:
            str: date (mm-yyyy) as a string and date of the blogs last update
        """            
        cursor = mysql.cursor()
        
        query = ('''select registered, last_updated from wp_blogs where blog_id = "%s"''')
                    # and meta_value like '%administrator'
        cursor.execute(query, (user_id,))

        results = cursor.fetchall()
        reg_dates = ""
        updates = ""

        for r in results:
            reg_dates = str(r[0]).split(" ")[0] 
            year_month = (f"{reg_dates[:7]}%")         
            updates = str(r[1]).split(" ")[0]

        cursor.close()

        return str(year_month), updates
    

    def get_year_regs(self,date,mysql) -> int:
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
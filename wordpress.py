from typing import List
import requests
import json
import base64
import colorama
from colorama import Fore, Back
import sys

class wp:
    def __init__(self, url: str = "https://localhost", username: str = "", password: str = "") -> None:
        self.url = url
        self.api_url = f"{self.url}/wp-json/wp/v2/"
        self.username = username
        self.password = password
        self.make_cred()
        self.headers = {'Authorization': f'Basic {self.token}'}


    def __str__(self) -> str:
        return f"<wp({self.url})>"
    

    def get_users(self, user, mysql) -> List[str]:
        # response = requests.get(f"{self.api_url}users", headers = self.headers)
        # data = response.json()
        # print(data)
        # return [u['slug'] for u in data]
    
        cursor = mysql.cursor()
            
        query = ('''select id, user_login')
                    from wp_users''')
        cursor.execute(query)

        for(id, user_login) in cursor:
            user [id] = user_login

        cursor.close()
    

    def delete_user(self, userID, userLogin, mysql) -> None:
        cursor = mysql.cursor()
        
        query = (f'''delete from wp_users where ID = {userID} and user_login = {userLogin}''')
        cursor.execute(query)
        
        cursor.close()


    def delete_blog(self, blogID, blogPath, mysql) -> None:
        cursor = mysql.cursor()
        
        query = (f'''delete from wp_blogs where user_id = {blogID} and path = "{blogPath}"''')
        cursor.execute(query)
        
        cursor.close()
    
    def get_posts(self) -> List[str]:  
        response = requests.get(f"{self.api_url}posts")
        if response.status_code != 200:
            return []
        # results = []
        # for post in response.json():
        #     results.append(post["title"]["rendered"])
        # return results
        return [post["title"]["rendered"] for post in response.json()]
    

    def make_cred(self) -> None:
        credentials = self.username + ":" + self.password
        self.token = base64.b64encode(credentials.encode()).decode('utf-8')

    
    def get_inactive_users(self, exclude: list[str] = [], blogs_users: list[str] = []) -> List[str]:
        """Finds the difference between the list of current users and all active users 
            (all_users.txt) on blogs.butler.edu

        Args:
            exclude (list[str], optional): _description_. Defaults to [].
            blogs_users (list[str], optional): _description_. Defaults to [].

        Returns:
            List[str]: _description_
        """
        all_users = set(line.strip().lower() for line in open('all_users.txt')
                        if line.strip() not in exclude)
        # blogs_users = set(line.strip().lower() for line in open('blogs_users.txt')
        #                   if line.strip() not in exclude)
        difference = set(blogs_users).difference(all_users) #the ones that aren't in both; returns users that are in blogs and not active
        intersect = set(blogs_users).intersection(all_users) #the ones that are in both; returns active blogs users
        return difference
    

    def get_site_users(self, slug: str = "/") -> List[str]:
        """Gets the users for a specific site.

        Args:
            slug (str, optional): _description_. Defaults to "/".

        Returns:
            List[str]: _description_
        """       
        colorama.init(autoreset=True)
        site_url = f"{self.url}{slug}wp-json/wp/v2/users"
        response = requests.get(site_url, headers = self.headers)
        if response.status_code == 200:
            data = response.json()
            return [int(item["id"]) for item in data]
        else:
            print(f"{Fore.WHITE}{Back.BLACK}Status code {response.status_code} on {slug}{Back.RESET}")
            # sys.exit()
            return []
            

    def get_id_username(self, id_username, mysql) -> None: 
        """Gets the id and username of blogs users with Butler emails.

        Args:
            id_username (_type_): _description_
            mysql (_type_): _description_
        """        
        # cnx = mysql.connector.connect(user="wordpress", password="4AbyJVrcPTH6aHgfAqt3", host="mysql-1.butler.edu", database="wp_blogs_dev")
        cursor = mysql.cursor()
        
        query = ('''select id, user_email 
                    from wp_users''')
                    # where user_email like "%@butler.edu"
        cursor.execute(query)

        for(id, user_email) in cursor:
            id_username [id] = user_email.split('@')[0]

        cursor.close()
        # cnx.close()

    
    def get_user_blogs(self, user_blogs, mysql) -> None: 
        """Gets all the blog ids and blog paths.

        Args:
            user_blogs (_type_): _description_
            mysql (_type_): _description_
        """        
        cursor = mysql.cursor()

        query = ('''select blog_id, path 
                    from wp_blogs''')
        cursor.execute(query)

        for(blog_id, path) in cursor:
            user_blogs [blog_id] = path
        
        cursor.close()


    def get_outside_users(self, outside_users, mysql) -> None:
        """Gets the id, username, and registration date of blogs users with non-Butler emails.

        Args:
            outside_users (_type_): _description_
            mysql (_type_): _description_
        """        
        cursor = mysql.cursor()
        
        query = ('''select id, user_email, DATE_FORMAT(user_registered,'reg-date: %m-%d-%Y')
                    from wp_users 
                    where user_email not like "%@butler.edu"''')
        cursor.execute(query)

        for(id, user_email, user_registered) in cursor:
            outside_users [id, user_registered] = user_email

        cursor.close()
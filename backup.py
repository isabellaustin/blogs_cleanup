from lxml import etree
import xml.etree.ElementTree as etree
#https://lxml.de/tutorial.html
import json
import shutil
import requests
import subprocess
import os
from wordpress import wp
import mysql.connector


def main() -> None:
    site = "/isabellaustin/"

    # MAKE SITE SUBDIRECTORY
    parent_dir = cfg['export_dir'] #backups is parent in this case
    directory = site.split("/")[1]

    path = os.path.join(parent_dir, directory)
    os.mkdir(path)
    print("Directory '% s' created" % directory)
    
    # DOWNLOAD MEDIA
    blogs.export_site(site,path)
    blogs.get_attachments(site,path)

    # ZIP DIRECTORY AND MOVE TO 'BACKUPS'
    zip = shutil.make_archive(directory, 'zip', path)
    shutil.move(zip, parent_dir)

    # DELETE SUBDIRECTORY AND SITE
    shutil.rmtree(path)


def export_site(self,site: str = "",path: str = "") -> str:
    p = subprocess.run(f"wp export --dir={path} --url=https://blogs-dev.butler.edu{site} --path=/var/www/html", shell=True, capture_output=True)
    status = p.stdout
    output = status.decode()
    print(output)


def get_attachments(self,site: str = "",path: str = "") -> None:
    response = requests.get(f'https://blogs-dev.butler.edu{site}wp-json/wp/v2/media')
    print(response.json())
    attachment_urls = []
    file_dict = {}
    filename = ""

    for r in response.json():
        for key in r.keys():
            if key == 'guid':
                url = r[key]["rendered"].replace("blogs-dev", "blogs")
                filename = url.split("/")[-1]
                
                attachment_urls.append(url)
        file_dict [url] = filename

    for url in file_dict.keys():
        r = requests.get(url)

        file_path = os.path.join(path, file_dict[url])
        with open(file_path,'wb') as f:
            f.write(r.content)


if __name__ == "__main__":
    with open('config.json', 'r') as f:
        cfg=json.load(f)

    cnx = mysql.connector.connect(user=cfg["db_username"], password=cfg["db_password"], host="docker-dev.butler.edu", database="wp_blogs_dev")

    blogs = wp(url = cfg["url"],
                username = cfg["username"],
                password = cfg["password"])

    main()
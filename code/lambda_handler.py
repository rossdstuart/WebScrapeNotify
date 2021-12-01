# import json
import sys
import urllib
import boto3
import botocore
import os
from bs4 import BeautifulSoup
from difflib import Differ
import re
from urllib.request import urlopen


def lambda_handler(event, context):
       ## Envs
       # print(os.environ)

       #pull this in from the event
       # url="https://revbrew.com/shop"
       url="http://www.hopbutcher.com/"
       # url="https://www.target.com/p/lego-technic-mclaren-senna-gtr-42123/-/A-80130446?clkid=f853a519N333411ec82de6d0c81a02937&lnm=360518&afid=Slickdeals_LLC&ref=tgt_adv_xasd0002"
       #pull this in from the template
       BucketName = os.environ.get('S3BucketName')
       SnsTopic = os.environ.get('TOPIC_ARN')
       
       print("scraping url")
       s3 = boto3.resource('s3')
       my_bucket = s3.Bucket(BucketName)

       #initialize sns client
       sns = boto3.client("sns")
       
       #try butifoual soup
       page = urlopen(url)
       html = page.read().decode("utf-8")
       soup = BeautifulSoup(html, "html.parser")
       data = soup.get_text()

       

       #set vars
       new_file_path = "new.html"
       old_file_path = "old.html"

       #put current webscrap to s3
       obj = s3.Object(BucketName,new_file_path) 
       obj.put(Key=new_file_path, Body=data, ContentType='text/html')

       ## Check if old.html exists
       try:
              s3.Object(BucketName, old_file_path).load()
       except botocore.exceptions.ClientError as e:
              if e.response['Error']['Code'] == "404":
                     print("old.html dosent exist")
                     print("copy new to old for first run")
                     s3.Object(BucketName, old_file_path).copy_from(CopySource=f"{BucketName}/{new_file_path}")


       
       ### set file paths and download files from S3
       new_path = f"/tmp/{new_file_path}"
       old_path = f"/tmp/{old_file_path}"
       s3.Bucket(BucketName).download_file(new_file_path, new_path)
       s3.Bucket(BucketName).download_file(old_file_path, old_path)
       #move new file to old
       s3.Object(BucketName, old_file_path).copy_from(CopySource=f"{BucketName}/{new_file_path}")


       i = 0
       message = ''
       with open(new_path) as file_1, open(old_path) as file_2:
              differ = Differ()
              # differ = SequenceMatcher()
              
              for line in differ.compare(file_1.readlines(), file_2.readlines()):
              # for line in SequenceMatcher(file_1.readlines(), file_2.readlines()).ratio():
                     # re.match('^\+', line)
                     compare = re.findall('^\-|^\+', line)
                     # print(compare)
                     if len(compare) != 0:
                            # print("No match")
                            i += 1
                            print(line)
                            #combine message
                            message += line

       if i == 0:
              print("no changes")
              # sns.publish(TopicArn=SnsTopic, 
              #        Message="no changes", 
              #        Subject="WebScrapper Notify")
       else:
              print("site has changed")
              #Publish to SNS
              # publish_message(SnsTopic, "this is a test message on topic")
              sns.publish(TopicArn=SnsTopic, 
                     Message=message, 
                     Subject="WebScraper Notify")
              #exit program
              sys.exit(i)
       

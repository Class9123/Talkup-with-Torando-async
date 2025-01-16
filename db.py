from datetime import datetime
from pymongo import MongoClient

class Mongodb:
  def __init__(self , uri , db_name ):
    self.uri = uri
    self.db_name = db_name 

  def connect(self):
    try:
      client = MongoClient(self.uri)
      self.db = client[self.db_name]
      print("Conncted successfully ") 
      print (f"Available collections are {self.db.list_collection_names()}")
    except Exception:
      raise ValueError("Cannot connect with "+ self.uri)
    self.users = self.db["Users"]
    self.messages = self.db["Messages"]    
  
  def add_user(self , user):
    # user ={ _id : "id"(inserted by mongo itself ) , name:"from email" , password:"password" , "email","jayjaygovind4@gmail.com" , friends : [Id ,...,] ,status:"online" }
    result = self.users.insert_one(user)
    return result.inserted_id
    
  def find_user(self , data):
    return self.users.find_one(data)
    
  def add_message(self,senderId, receiverId , time , text="" , url="" , ):
    message = {
        "senderId": senderId,
        "receiverId": receiverId,
        "text": text,
        "image":url,
        "time":time,
        "timestamp": datetime.utcnow()
        }
    return self.messages.insert_one(message)
    
  def get_messages(self, userId, friendId):
    return self.messages.find(
        {
            "$or": [
                {"senderId": userId, "receiverId": friendId},
                {"senderId": friendId, "receiverId": userId}
            ]
        },
        {"_id": 0, "timestamp": 0}  # Exclude the "_id" and "timestamp" field
    ).sort("timestamp", 1)
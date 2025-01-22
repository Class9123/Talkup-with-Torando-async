import asyncio
import os
from bson import ObjectId
from json import loads, dumps
from tornado.web import RequestHandler as baseRsClass, StaticFileHandler, Application
from socketio import AsyncServer, get_tornado_handler

#my classes and functions 
from db import AsyncMongodb
from values import DEV_MONGO_URI, DB_NAME
from utility import serialize_dict ,deserialize_dict,validate_email_password,extract_username,key_from_value
from imageDb import upload_image_in_thread


sio = AsyncServer(async_mode="tornado", cors_allowed_origins=["http://localhost:5000"])
mongo = AsyncMongodb(DEV_MONGO_URI, DB_NAME)
ids = {}  # { Dbid: socketId}
verified = {}  # { "sid" : True or False ,..}

class RequestHandler( baseRsClass):
  pass
class Assets(StaticFileHandler):
  def initialize(self, path):
    self.root = path

  def set_default_headers(self):
    super().set_default_headers()
    self.set_header("Access-Control-Allow-Origin", "http://localhost:5000")
    self.set_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
    self.set_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
    self.set_header("Access-Control-Allow-Credentials", "true")
class CatchAll(RequestHandler):
  def get(self, path):
    self.render("dist/index.html")    

class Login(RequestHandler):
  async def post(self): 
    data = loads(self.request.body)
    email = data.get("email").strip()
    password = data.get("password").strip()
    if not email or not password:
      print("Email or password not found")
      self.set_status(500)
      self.write({"isLoggedIn": "False", "message": "Email and password are required."})
      return
    query = {"email": email, "password": password}
    result = await mongo.find_user(query)
    if result:
      result["id"] = result.pop("_id")
      result.pop("friends", None) 
      print(f"\nLogged in: {result}\n")
      self.set_status(200)
      self.write({"Login":True , "credentials": serialize_dict(result) , "msg":"Logined successfully"})
      return 
    self.set_status(200)
    self.write({"Login":False , "msg" :"Invalid password,Try your best "})
    return
  def get(self):
    self.redirect("/")

class Signup(RequestHandler):
  async def post(self):
    data = loads(self.request.body)
    email = data.get("email")
    password = data.get("password")
    confirmpassword = data.get("confirmpassword")
    if not email or not password or not confirmpassword:
      self.set_status(400)
      self.write({"msg": "All fields are required!"})
      return
    result = validate_email_password(email, password, confirmpassword)
    if result is True:
      name = extract_username(email)
      user = {"name": name, "email": email, "password": password, "status": "offline", "friends": [], "pr": "https://res.cloudinary.com/dfppd4tl7/image/upload/ej6rfibaerbrlztgpvah"}
        # friends:[ friendobjectid, .... ]
      query = {"email": email}
      
      if await mongo.find_user(query) is not None:
        self.set_status(400)
        self.write({"msg": "Account with same email already exist!"})
        return 
      userId = await mongo.add_user(user)
      user["id"] = userId
      user.pop("_id", None)
      print(f"\nUser Signuped: {user}\n")
      self.set_status(200)
      self.write({"msg": "Account created successfully 🎊🎉", "credentials": serialize_dict(user)})
      return 
    self.set_status(400)
    self.write ({"msg": result})
    
@sio.event
async def disconnect(Usersid):
  print("Disconnected by ", Usersid)
  print("Logginout thw user ")
  Id = key_from_value(ids, Usersid)
  if not Id:
    print(f"Disconnect: No user found for sid {Usersid}")
    return
  query = {"_id": Id}
  result = await mongo.find_user(query)
  if not result:
    print(f"Disconnect: User {Id} not found in the database")
    return
  # Set the user status to offline
  await mongo.users.update_one(query, {"$set": {"status": "offline"}})
  print(f"User {Id} is now offline")
  for fid in result["friends"]:
    friendSid = ids.get(fid)
    if friendSid:
      print(f"Notifying friend {fid} about user {Id} status")
      await sio.emit("make_friend_offline", str(Id), to=friendSid)
    else:
      print(f"Friend {fid} is not connected")
      
  ids.pop(Id, None)
  verified.pop(Usersid,None)

@sio.event 
async def register(Usersid , credentials):
  keys_to_check = ["id", "name", "email", "password", "status"]
  all_exist = all(key in credentials for key in keys_to_check)
  if not all_exist:
    return
  Id = credentials["id"]
  email = credentials["email"]
  password = credentials["password"]
  
  y_query = {"_id": ObjectId(Id), "email": email, "password": password}
  y_result = await mongo.find_user(y_query)
  if y_result:
    dbId = y_result["_id"]
    ids[dbId] = Usersid
    verified[Usersid] = True
    data = []
    # send friends data after the registration 
    for friendid in y_result["friends"]:
      query = {"_id": friendid}
      result = await mongo.find_user(query)
      if result:
        result["id"] = result.pop("_id")
        result["msg"] = ""
        result.pop("password")
        result.pop("friends")
        result = serialize_dict(result)
        data.append(result)
    print(f"Register by {Usersid}")
    await mongo.users.update_one(y_query, {"$set": {"status": "online"}})
    await sio.emit("take_friends", data, to=Usersid)
    for fid in y_result["friends"]:
      friendSid = ids.get(fid)
      if friendSid:
        print(f"Notifying friend {fid} about user {Id} status")
        await sio.emit("update_friend", str(Id), to=friendSid)
      else:
        print(f"Friend {fid} is not connected")

@sio.event
async def addFriend(sid, data):
  if not verified.get(sid):
    msg = "You are not authenticated"
    await sio.emit("added", msg, to=sid)
    return

  fem = data["femail"].strip()
  yem = data["yemail"].strip()

  if fem == yem:
    msg = "You are trying to add yourself"
    await sio.emit("added", msg, to=sid)
    return

  fquery = {"email": fem}
  yquery = {"email": yem}

  ydocument = await mongo.find_user(yquery)
  if ydocument is None:
    msg = "You are not verified"
    await sio.emit("added", msg, to=sid)
    return

  fdocument = await mongo.find_user(fquery)
  if fdocument is None:
    msg = "Friend not found"
    await sio.emit("added", msg, to=sid)
    return

  if fdocument["_id"] in ydocument["friends"]:
    msg = "Friend is already added"
    await sio.emit("added", msg, to=sid)
    return

  await mongo.users.update_one({"email": yem}, {"$push": {"friends": fdocument["_id"]}}) 
  await mongo.users.update_one({"email": fem}, {"$push": {"friends": ydocument["_id"]}})
  print(f"Added {fem} to {yem}")

  ydocument["id"] = ydocument.pop("_id")
  ydocument["msg"] = ""
  ydocument.pop("password")
  ydocument.pop("friends")

  fdocument["id"] = fdocument.pop("_id")
  fdocument["msg"] = ""
  fdocument.pop("password")
  fdocument.pop("friends")

  await sio.emit("added", [f"Added {fdocument['email']}", serialize_dict(fdocument)], to=sid)
  if ids.get(fdocument["id"]):
    await sio.emit("added", [f"{ydocument['email']} added you", serialize_dict(ydocument)], to=ids[fdocument["id"]]) 
    
@sio.event
async def get_friend_data(sid, fid):
  query = {"_id": ObjectId(fid)}
  result = await mongo.find_user(query)
  if result:
    result["id"] = result.pop("_id")
    result["msg"] = ""
    result.pop("password")
    result.pop("friends")
    result = serialize_dict(result)
    await sio.emit("friend_data", result, to=sid)
  else:
    await sio.emit("remove_friend", fid, to=sid)

@sio.event
async def get_messages(sid, friendId):
  userId = key_from_value(ids, sid)
  if userId:
    friendId = ObjectId(friendId)
    result = await mongo.get_messages(userId, friendId)
    result = [serialize_dict(obj) for obj in result]
    await sio.emit("messages", result, to=sid)

@sio.event
async def send_message(sid, data):
  data = deserialize_dict(data)
  userId = key_from_value(ids, sid)
  if userId:
    friendId = data["id"]
    text = data["text"]
    time = data["time"]
    image = data["image"]
    await mongo.add_message(userId, friendId, time, text, image)
    data["friendId"] = data.pop("id")
    data["senderId"] = userId
    if ids.get(friendId):
      await sio.emit("message", serialize_dict(data), to=ids[friendId])

@sio.event
async def profileImageUpdate(sid, data):
  user_id = key_from_value(ids, sid)
  if user_id:
    image_data = data.get("image")
    print(image_data[0:100])
    url = await upload_image_in_thread(image_data)
    query = {"_id": user_id}
    result = await mongo.find_user(query)
    if result:
      await mongo.users.update_one(query, {"$set": {"pr": url}})
      await sio.emit("prUrl", {"url": url}, to=sid)
      for fid in result["friends"]:
        friend_sid = ids.get(fid)
        if friend_sid:
          await sio.emit("update_friend", str(user_id), to=friend_sid)
        else:
          print(f"Friend {fid} is not connected")      

@sio.event
async def DeleteAccount(sid, credentials):
  credentials = deserialize_dict(credentials)
  userId = key_from_value(ids, sid)
  if userId == credentials["id"]:
    query = {"_id": credentials["id"], "email": credentials["email"], "password": credentials["password"]}
    result = await mongo.find_user(query)
    
    if result:
      for fid in result["friends"]:
        f_query = {"_id": fid}
        await mongo.users.update_one(
          f_query,
          {"$pull": {"friends": credentials["id"]}}
        )
      
      await sio.emit("account_deleted", to=sid)
      await disconnect(sid)
      await mongo.users.delete_one(query)


def make_app():
  return Application([
    (r"/socket.io/", get_tornado_handler(sio)),
    (r"/login", Login),
    (r"/signup", Signup),
    (r"/assets/(.*)", Assets, {"path": os.path.join(os.getcwd(), "dist/assets")}),
    (r"/(.*)", CatchAll),
  ], debug=True, autoreload=True)  

async def main():
  await mongo.connect()
  
  app = make_app()
  app.listen(5000 , address="0.0.0.0")
  print("server listening on port 5000")
  await asyncio.Event().wait()
    
if __name__ == "__main__":
  asyncio.run(main()) 
from db import Mongodb
from values import DEV_MONGO_URI , DB_NAME
from flask import Flask, request , jsonify 
from flask_socketio import SocketIO , emit
from flask_cors import CORS
from utility import validate_email_password,extract_username,serialize_dict,deserialize_dict, key_from_value
from bson import ObjectId
from imageDb import upload_image
import threading 

mongo = Mongodb(DEV_MONGO_URI , DB_NAME)
mongo.connect()
ids={   } # { Dbid: socketId}
verified = { } # { "sid" : True or False ,..}
app = Flask(__name__)
CORS(app)
sio = SocketIO(app, cors_allowed_origins="*")
    
@app.route('/signup', methods=['POST'])
def signup():
  data = request.json
  email = data.get("email")
  password = data.get("password")
  confirmpassword = data.get("confirmpassword")
  
  if not email or not password or not confirmpassword:
    return jsonify({"msg": "All fields are required!"}), 400
  # Validate email and password format
  result = validate_email_password(email, password, confirmpassword)
  if result is True:
    name = extract_username(email)
    user = {"name": name, "email": email, "password": password ,"status":"offline", "friends" :[] ,"pr":"profile.png" }
    # friends:[ friendobjectid , .... ]
    query ={"email" : email}
    
    if mongo.find_user(query) is not None:
      return jsonify({"msg": "Accout with same email already exist!"}), 400
    userId = mongo.add_user(user)
    user["id"] = userId
    user.pop("_id" , None)
    print(f"\n User Signuped : {user} \n")
    return jsonify({"msg": "Account created successfully 🎊🎉" , "credentials" : serialize_dict(user)}), 201
  return jsonify({"msg": result}), 400

@app.route('/login', methods=['POST'])
def login():
  data = request.json
  email = data["email"]
  password = data["password"]
  query = { "email":email , "password":password}
  result = mongo.find_user(query)
  if result is not None:
    result ["id"] = result.pop("_id")
    result.pop("friends")
    print(f"\nLogined : {result}\n")
    return jsonify({"isLoggedIn":"True" ,"credentials":serialize_dict(result)}) , 201
  return jsonify({"isLoggedIn":"False"}),400

@sio.on('disconnect')
def hande_disconnect():
  userSid = request.sid
  Id = key_from_value(ids, userSid)
  if not Id:
    print(f"Disconnect: No user found for sid {userSid}")
    return
  query = {"_id": Id}
  result = mongo.find_user(query)
  if not result:
    print(f"Disconnect: User {Id} not found in the database")
    return
  # Set the user status to offline
  mongo.users.update_one(query, {"$set": {"status": "offline"}})
  print(f"User {Id} is now offline")
  # Notify all friends

  for fid in result["friends"]:
    friendSid = ids.get(fid)
    if friendSid:
      print(f"Notifying friend {fid} about user {Id} status")
      emit("update_friend", str(Id), to=friendSid)
    else:
      print(f"Friend {fid} is not connected")
  # Remove the user from ids and verified
  ids.pop(Id, None)
  verified.pop(userSid, None)
  print(f"Cleaned up sid {userSid} for user {Id}")

@sio.on("register")
def register_give_friendlist(credentials):
  # for user validation 
  # { "id":.., "email":.., "password":.. ,   }
  keys_to_check = ["id", "name", "email", "password", "status"]
  all_exist = all(key in credentials for key in keys_to_check)
  if all_exist is not True:
    return 
  
  Id = credentials["id"]
  email = credentials ["email"]
  password = credentials["password"]
  
  y_query = { "_id":ObjectId(Id), "email":email , "password" : password} 
  y_result = mongo.find_user(y_query)
  dbId = y_result["_id"]
  ids[dbId] = request.sid
  verified[request.sid] = True
  
  data = []
  for friendid in y_result["friends"]:
    query = { "_id":friendid}
    result = mongo.find_user(query)
    result["id"] = result.pop("_id")
    result["msg"] = "Seee you soon grubnfn ynf y y yndkdufjr yvkfjeur gfbdyd yv a e"
    result.pop("password")
    result.pop("friends") 
    result = serialize_dict(result)
    data.append(result)
  print()  
  print (f"Regeister by {request.sid}")
  print(ids)
  print(verified)
  mongo.users.update_one(y_query , {"$set":{"status":"online"}})
  emit("take_friends" , data , to=request.sid )

  for fid in y_result["friends"]:
    friendSid = ids.get(fid)
    if friendSid:
      print(f"Notifying friend {fid} about user {Id} status")
      emit("update_friend", str(Id), to=friendSid)
    else:
      print(f"Friend {fid} is not connected")

@sio.on("addFriend") 
def add_friend(data):
  if not verified.get(request.sid):
    msg = "You are not authenticated"
    emit("added" , msg , to=request.sid)
    return

  fem = data["femail"].strip()
  yem = data["yemail"].strip()
  
  if fem==yem :
    msg = "You are trying to add yourself "
    emit("added" , msg , to=request.sid)
    return
  
  fquery = {"email" : fem}
  yquery = {"email" : yem}
  
  ydocument = mongo.find_user(yquery)
  if ydocument is None :
    msg = "Your are not verified "
    emit("added" , msg , to=request.sid)
    return
  
  fdocument = mongo.find_user(fquery)
  if fdocument is None:
    msg = "Friend not found"
    emit("added" , msg , to=request.sid)
    return 
  
  if fdocument["_id"] in  ydocument["friends"]:
    msg = "Friend is already added"
    emit("added" , msg , to=request.sid)
    return 
  mongo.users.update_one(
      {"email": yem},  
      {"$push": {"friends": fdocument["_id"]}}
      )
  
  mongo.users.update_one(
      {"email": fem},  
      {"$push": {"friends": ydocument["_id"]}}
      )
  print(f"Added {fem} to {yem}")
  
  ydocument["id"] = ydocument.pop("_id")
  ydocument["pr"] = "/pr.jpg"
  ydocument["msg"] = "Seee you soon grubnfn ynf y y yndkdufjr yvkfjeur gfbdyd yv a e"
  ydocument.pop("password")
  ydocument.pop("friends") 
  
 
  fdocument["id"] = fdocument.pop("_id")
  fdocument["pr"] = "/pr.jpg"
  fdocument["msg"] = "Seee you soon grubnfn ynf y y yndkdufjr yvkfjeur gfbdyd yv a e"
  fdocument.pop("password")
  fdocument.pop("friends") 
  
  emit("added" , [f"Added {fdocument['email']}" ,serialize_dict(fdocument)], to=ids[ydocument["id"]])
  if ids[fdocument ["id"]]:
    emit("added" , [ f"{ydocument['email']} added you" ,serialize_dict(ydocument)], to=ids[fdocument ["id"]])
    
@sio.on("get_friend_data")    
def get_friend_data(fid):
  query = { "_id": ObjectId(fid)}
  result = mongo.find_user(query)
  result["id"] = result.pop("_id")
  result["msg"] = "Updated friend"
  result.pop("password")
  result.pop("friends") 
  result = serialize_dict(result)
  emit("friend_data" , result , to=request.sid)
  
@sio.on("get_messages")
def get_messages(friendId):
  userSid = request.sid
  userId = key_from_value(ids , userSid)
  friendId = ObjectId(friendId)
  result = list(mongo.get_messages(userId , friendId))
  result = [serialize_dict(obj) for obj in result]
  emit("messages" ,result , to=userSid) 
  
@sio.on("send_message")  
def send_message(data):
  userSid = request.sid
  data = deserialize_dict(data)
  userId = key_from_value(ids , userSid)
  print(type(userId) , userId)
  print(data)
  friendId = data["id"]
  text = data["text"]
  time = data["time"]
  image = data["image"]
  mongo.add_message(userId, friendId, time , text , image)
  data["friendId"] = data.pop("id")
  data["senderId"] = userId
  if ids.get(friendId):
    print(data)
    emit("message" , serialize_dict(data) , to=ids[friendId])
    
def upload_image_in_thread(image_data, user_id , userSid):
  url = upload_image(image_data)
  query = {"_id": user_id}
  result = mongo.find_user(query)
  mongo.users.update_one( query ,{"$set": {"pr": url}})
  sio.emit("prUrl", {"url": url}, to=userSid)
  for fid in result["friends"]:
    friendSid = ids.get(fid)
    if friendSid:
      sio.emit("update_friend", str(user_id), to=friendSid)
    else:
      print(f"Friend {fid} is not connected")  

@sio.on("profileImageUpdate")
def profile_update(data):
  userId = key_from_value(ids, request.sid)
  image_data = data["image"]
  # Use `sio.start_background_task` instead of threading directly
  sio.start_background_task(target=upload_image_in_thread, image_data=image_data, user_id=userId, userSid=request.sid)

    
if __name__ == '__main__':
  mongo.users.delete_many({})
  mongo.messages.delete_many({})
  sio.run(app , debug=True) 
  #public fields = id ,name , email , status
  #private fields = password, friends 
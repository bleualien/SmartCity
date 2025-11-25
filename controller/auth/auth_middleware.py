import jwt
from functools import wraps
from flask import request, jsonify, current_app
from models.user_model import User  


#middleware function to protect routes
def token_required(f): #check JWT tokens for protected routes and feteches the 
    #current logged in user and then passes curret_user to the route function
    @wraps(f)
    def decorated(*args, **kwargs): #decorated()= function that will run before the original endpoint
        token = None
        auth_header= request.headers.get('Authorization')
        #initializing token variable
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        # token vayena vane User cannot access protected route
        if not token:
            return jsonify({"error": "Token is missing!"}), 401

        try:
            # Decoding token= token valid xaki xaina vanera check garne
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])

            # Fetching the user from DB so the logged-in user is known without manually sending ID in URL
            user_id = data.get("id")
            current_user = User.query.get(user_id)

            if not current_user: #matching user xaina vane request lai deny garne
                return jsonify({"error": "Invalid user"}), 401

        # if token expired or invalid xa vane 
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        except Exception as e:
            return jsonify({"error": f"Token validation failed: {str(e)}"}), 401


        # if token valid ya user exists vane pass the authenticated user to the endpoint
        return f(current_user, *args, **kwargs)

    return decorated

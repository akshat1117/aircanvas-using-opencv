import cv2
import os
import numpy as np
from flask import Flask, render_template, Response, request, redirect, session, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import HandTracking as ht

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SECRET_KEY"] = "My SUper Secret Key"
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.Text, nullable=False)

@app.route('/')
def index():
    if 'user_id' not in session:
        return render_template("index.html", logged_in=False)
    curr_user = User.query.get(session['user_id'])
    return render_template("index.html", logged_in=True, curr_user=curr_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect('/')
        else:
            flash('Invalid email or password', 'danger')
            return redirect('/login')
        
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()

        if existing_user:
            flash('Username or email already exists. Please choose a different one.', 'danger')
        else:
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()

            flash('Account created successfully. Please log in.', 'success')
            return redirect(url_for('login'))

    return render_template('/auth/register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/')

@app.route('/aircanvas')
def aircanvas():
    return render_template('aircanvas.html')  # Render your aircanvas.html template

@app.route('/meeting')
def meeting():
    if 'user_id' not in session:
        flash('You need to be logged in to access this page', 'danger')
        return redirect('/')
    
    curr_user = User.query.get(session['user_id'])
    return render_template("meeting.html", curr_user=curr_user)

@app.route('/join', methods=['GET', 'POST'])
def join_meeting():
    if request.method == 'POST':
        meeting_id = request.form.get('room_id')
        return redirect(f'/meeting?roomID={meeting_id}')
    return render_template("join_meeting.html")

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def generate_frames():
    folder_path = "Header"
    my_list = os.listdir(folder_path)
    palette = []
    canvas = np.zeros((720, 1280, 3), np.uint8)
    pt_size = 60
    thickness = 30
    current_color = (0, 0, 0)
    x_prev, y_prev = 0, 0

    # Reading in color palette overlay
    for im_path in my_list:
        image = cv2.imread(f'{folder_path}/{im_path}')
        palette.append(image)

    # Setting default to eraser and adjusting sizing
    header = palette[my_list.index('eraser.jpg')]
    cap = cv2.VideoCapture(0)
    cap.set(3, 1280)
    cap.set(4, 720)

    # Creating hand detector
    detector = ht.HandDetector(detection_confidence=0.85)

    while True:

        # Importing and flipping image
        ret, img = cap.read()
        img = cv2.flip(img, 1)
        # Finding hand landmark with module
        img = detector.find_hands(img)
        lm_list = detector.find_position(img, draw=False)

        if len(lm_list) != 0:
            # Collecting x and y coords of index and middle finger
            x_index, y_index = lm_list[8][1:3]
            x_middle, y_middle = lm_list[12][1:3]
            # Check which fingers are up
            fingers = detector.fingers_up()
            # If selection mode - Two fingers up
            if fingers[1] == 1 and fingers[2] == 1:
                x_prev, y_prev = 0, 0
                cv2.circle(img, (x_index, y_index), 15, (255, 255, 255), cv2.FILLED)
                # Color setting based on x coordinate of index finger
                if y_index < 130:
                    # Eraser
                    if 0 < x_index < 164:
                        header = palette[my_list.index('eraser.jpg')]
                        current_color = (0, 0, 0)
                    # White
                    elif 165 < x_index < 369:
                        header = palette[my_list.index('white.jpg')]
                        current_color = (255, 255, 255)
                    # Purple
                    elif 370 < x_index < 474:
                        header = palette[my_list.index('purple.jpg')]
                        current_color = (235, 23, 94)
                    # Red
                    elif 475 < x_index < 639:
                        header = palette[my_list.index('red.jpg')]
                        current_color = (22, 22, 255)
                    # Orange
                    elif 640 < x_index < 799:
                        header = palette[my_list.index('orange.jpg')]
                        current_color = (77, 145, 255)
                    # Yellow
                    elif 800 < x_index < 954:
                        header = palette[my_list.index('yellow.jpg')]
                        current_color = (89, 222, 255)
                    # Green
                    elif 955 < x_index < 1109:
                        header = palette[my_list.index('green.jpg')]
                        current_color = (87, 217, 126)
                    # Blue
                    elif 1110 < x_index < 1280:
                        header = palette[my_list.index('blue.jpg')]
                        current_color = (255, 182, 56)

            # If draw mode - Index finger up
            if fingers[1] == 1 and fingers[2] == 0:
                cv2.circle(img, (x_index, y_index), pt_size, current_color, cv2.FILLED)
                if x_prev == 0 and y_prev == 0:
                    x_prev, y_prev = x_index, y_index
                # Adjusting the thickness and point size between erase and draw
                if current_color == (0, 0, 0):
                    thickness = 60
                    pt_size = 30
                else:
                    thickness = 10
                    pt_size = 10

                # Drawing lines
                cv2.line(img, (x_prev, y_prev), (x_index, y_index), current_color, thickness)
                cv2.line(canvas, (x_prev, y_prev), (x_index, y_index), current_color, thickness)
                x_prev, y_prev = x_index, y_index

        # Creating a gray image
        img_gray = cv2.cvtColor(canvas, cv2.COLOR_BGR2GRAY)
        # Produces an inverse image which creates black areas on where drawing happens
        _, img_inv = cv2.threshold(img_gray, 50, 255, cv2.THRESH_BINARY_INV)
        img_inv = cv2.cvtColor(img_inv, cv2.COLOR_GRAY2BGR)
        # Adding the image with the inverse image
        img = cv2.bitwise_and(img, img_inv)
        # Or condition to integrate the colored drawing canvas with the B/W image
        img = cv2.bitwise_or(img, canvas)
        # Display the color palette overlay and screen
        img[0: 130, 0:1280] = header
        img = cv2.addWeighted(img, 0.5, canvas, 0.5, 0)

        ret, buffer = cv2.imencode('.jpg', img)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

if __name__ == '__main__':
    app.run(debug=True)

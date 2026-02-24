from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)

# --- DATABASE CONFIGURATION ---
# Get the URL from Render's environment variable, or use local SQLite for testing
db_url = os.environ.get('DATABASE_URL', 'sqlite:///inventory.db')

# Fix for Render: SQLAlchemy requires "postgresql://" instead of "postgres://"
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- DATABASE MODELS ---

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    models = db.relationship('VehicleModel', backref='group', cascade="all, delete-orphan", lazy=True)

class VehicleModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    items = db.relationship('Item', backref='vehicle_model', cascade="all, delete-orphan", lazy=True)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    qty = db.Column(db.Integer, default=0)
    min_qty = db.Column(db.Integer, default=0)
    model_id = db.Column(db.Integer, db.ForeignKey('vehicle_model.id'), nullable=False)

# Initialize database
with app.app_context():
    db.create_all()

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data', methods=['GET'])
def get_data():
    groups = Group.query.all()
    output = []
    for g in groups:
        g_data = {'id': g.id, 'name': g.name, 'models': []}
        for m in g.models:
            m_data = {'id': m.id, 'name': m.name, 'items': []}
            for i in m.items:
                m_data['items'].append({'id': i.id, 'name': i.name, 'qty': i.qty, 'min': i.min_qty})
            g_data['models'].append(m_data)
        output.append(g_data)
    return jsonify(output)

@app.route('/api/group', methods=['POST'])
def add_group():
    data = request.json
    new_group = Group(name=data['name'])
    db.session.add(new_group)
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/model', methods=['POST'])
def add_model():
    data = request.json
    new_model = VehicleModel(name=data['name'], group_id=data['group_id'])
    db.session.add(new_model)
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/item', methods=['POST'])
def add_item():
    data = request.json
    if 'id' in data and data['id']:
        item = Item.query.get(data['id'])
        item.name = data['name']
        item.qty = data['qty']
        item.min_qty = data['min']
    else:
        item = Item(name=data['name'], qty=data['qty'], min_qty=data['min'], model_id=data['model_id'])
        db.session.add(item)
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/item/adjust', methods=['POST'])
def adjust_item():
    data = request.json
    item = Item.query.filter_by(name=data['name'], model_id=data['mid']).first()
    if item:
        item.qty = max(0, item.qty + data['adj'])
        db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/delete/<type>/<id>', methods=['DELETE'])
def delete_entry(type, id):
    target = None
    if type == 'g': target = Group.query.get(id)
    elif type == 'm': target = VehicleModel.query.get(id)
    elif type == 'i': target = Item.query.get(id)
    
    if target:
        db.session.delete(target)
        db.session.commit()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    # Use PORT from environment for Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    

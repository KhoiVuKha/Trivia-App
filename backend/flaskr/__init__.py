import os
from flask import Flask, request, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import random

from models import setup_db, Question, Category, db

QUESTIONS_PER_PAGE = 10

def paginate_questions(request, selection):
    page = request.args.get("page", 1, type=int)
    start = (page - 1) * QUESTIONS_PER_PAGE
    end = start + QUESTIONS_PER_PAGE

    questions = [question.format() for question in selection]
    current_questions = questions[start:end]

    return current_questions

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)
    setup_db(app)

    # Set up CORS. Allow '*' for origins.
    CORS(app)

    # Use the after_request decorator to set Access-Control-Allow
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Headers', 'GET, POST, PATCH, DELETE, OPTIONS')
        return response

    # An endpoint to handle GET requests for all available categories.
    @app.route('/categories')
    def get_categories():
        categories = Category.query.order_by(Category.id).all()

        # Imidiately return if category empty.
        if len(categories) == 0:
            abort(404)

        # Get dictionary of categories
        category_dict = {}
        for category in categories:
            category_dict[category.id] = category.type

        return jsonify({
                "success": True,
                "categories": category_dict
            }
        )

    # An endpoint to handle GET requests for questions, including pagination (every 10 questions).
    @app.route('/questions')
    def get_questions():
        selection = Question.query.order_by(Question.id).all()
        categories = Category.query.all()

        # Get dictionary of categories:
        category_dict = {}
        for category in categories:
            category_dict[category.id] = category.type

        # Get current questions
        current_questions = []
        if len(selection) > 0:
            current_questions = paginate_questions(request, selection)

        if len(current_questions) == 0:
            abort(404)

        return jsonify(
            {
                "success": True,
                "questions": current_questions,
                "total_questions": len(selection),
                "current_category": [], # currently this field doesn't contain any data.
                "categories": category_dict
            }
        )

    # An endpoint to DELETE question using a question ID.
    @app.route("/questions/<int:question_id>", methods=["DELETE"])
    def delete_question(question_id):
        try:
            # Get question/list of question that has/have id = question_id
            question = Question.query.filter(Question.id == question_id).one_or_none()

            if question is None:
                abort(404)

            # Delete the selected question 
            question.delete()

            # Get the remain questions
            remain_questions = Question.query.order_by(Question.id).all()
            current_questions = paginate_questions(request, remain_questions)

            return jsonify({
                    "success": True,
                    "deleted": question_id,
                    "questions": current_questions,
                    "total_questions": len(remain_questions)
                }
            )

        except:
            db.session.rollback()
            abort(422) # Un Processable

    # An endpoint to POST a new question, which will require the question and answer text, category, and difficulty score.
    @app.route("/questions", methods=["POST"])
    def create_question():
        body = request.get_json()

        # Prepare data for the new question
        new_question = body.get("question", None) # Get will return "question" if match else automatically return "None".
        new_answer = body.get("answer", None)
        new_difficulty = body.get("difficulty", None)
        new_category = body.get("category", None)

        try:
            # Create new Question model
            question = Question (
                question = new_question, 
                answer = new_answer, 
                difficulty = new_difficulty,
                category = new_category
            )

            # Insert new question to database
            question.insert()

            # Get list of questions after insert
            selection = Question.query.order_by(Question.id).all()
            current_questions = paginate_questions(request, selection)

            return jsonify({
                "success": True,
                "questions": current_questions,
                "total_questions": len(selection),
                "created": question.id
            })

        except:
            db.session.rollback()
            abort(422) # Un Processable

    """
    A POST endpoint to get questions based on a search term. 
    It should return any questions for whom the search term is a substring of the question.
    """
    @app.route('/questions/search', methods=['POST'])
    def search_questions():
        body = request.get_json()
        search = body.get('searchTerm', None)

        if search:
            print("Search for question with searchTerm: ", search)
            selection = Question.query \
                .order_by(Question.id) \
                .filter(Question.question.ilike("%{}%".format(search))) \
                .all()
            
            # Get list of question that match the search term
            questions = paginate_questions(request, selection)

            return jsonify({
                'success': True,
                'questions': questions,
                'total_questions': len(selection),
                'current_category': [] # currently this field doesn't contain any data.
            })
        else:
            abort(404) # Question searching not found

    # Create a GET endpoint to get questions based on category.
    @app.route('/categories/<int:category_id>/questions', methods=['GET'])
    def get_questions_of_category(category_id):
        selection = Question.query \
            .order_by(Question.id) \
            .filter(Question.category == category_id) \
            .all()

        if len(selection) == 0:
            abort(404) # Not found - no question for this category id

        # Get list of question
        questions = paginate_questions(request, selection)

        return jsonify({
            'success': True,
            'questions': questions,
            'total_questions': len(selection),
            'current_category': category_id
        })

    @app.route('/quizzes', methods=['POST'])
    def play_quiz():
        body = request.get_json()
        
        # Prepare data to get a new quiz
        previous_questions = body.get('previous_questions')
        quiz_category = body.get('quiz_category')
        
        try:
            list_remain_questions = []   
            if quiz_category is None:
                list_remain_questions = Question.query \
                    .filter(Question.id.notin_((previous_questions))) \
                    .all()
            else:
                list_remain_questions = Question.query \
                    .filter_by(category=quiz_category['id']) \
                    .filter(Question.id.notin_((previous_questions))) \
                    .all()

            if len(list_remain_questions) < 1:
                abort(404) # Not found - No question found

            new_question = random.choice(list_remain_questions).format()

            return jsonify({
                'success': True,
                'question': new_question
            })
        except:
            abort(422) # Un processable.

    # Error handlers for all expected errors
    @app.errorhandler(400)
    def bad_request(error):
        return (
            jsonify({"success": False, 
                     "error": 400, 
                     "message": 
                     "Bad Request"}),
            400
        )
    
    @app.errorhandler(404)
    def not_found(error):
        return (
            jsonify({"success": False, 
                     "error": 404, 
                     "message": "Not Found"}),
            404
        )

    @app.errorhandler(422)
    def unprocessable(error):
        return (
            jsonify({"success": False, 
                     "error": 422, 
                     "message": "Unprocessable"}),
            422
        )
    
    @app.errorhandler(500)
    def internal_server_error(error):
        return (
            jsonify({"success": False, 
                     "error": 500, 
                     "message": "Internal Server Error"}),
            500
        )

    return app


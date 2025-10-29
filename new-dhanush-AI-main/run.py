from app import create_app

# Create the Flask app using factory pattern
app = create_app()

if __name__ == "__main__":
    # For local testing
    app.run(host="0.0.0.0", port=5000, debug=True)  # Set debug=False in production

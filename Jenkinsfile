pipeline {
    agent any

    stages {

        stage('Clone Repository') {
            steps {
                echo "Cloning repository..."
                git branch: 'main', url: 'https://github.com/Nakul-M/voicebot-ec2-jenkins.git'
            }
        }

        stage('Setup Python Environment') {
            steps {
                echo "Setting up Python virtual environment..."
                sh '''
                set -e

                echo "Python version:"
                python3 --version

                echo "Creating virtual environment..."
                python3 -m venv venv

                echo "Activating venv..."
                . venv/bin/activate

                echo "Upgrading pip..."
                pip install --upgrade pip

                echo "Installing requirements..."
                pip install -r requirements.txt
                '''
            }
        }

        stage('Check Ollama Server') {
            steps {
                sh '''
                echo "Checking Ollama server..."
                curl -v http://172.26.13.25:11434
                '''
            }
        }

        stage('Run Voicebot') {
            steps {
                sh '''
                set -e

                echo "Starting voicebot..."

                chmod +x scripts/run.sh

                echo "Running run.sh script..."
                bash scripts/run.sh

                echo "Checking if port 8080 opened..."

                sleep 5

                echo "Processes running:"
                ps aux | grep python || true

                echo "Port check:"
                lsof -i :8080 || true

                echo "Last 20 lines of app.log:"
                tail -n 20 app.log || true
                '''
            }
        }
    }

    post {
        success {
            echo "Voicebot deployed successfully!"
        }

        failure {
            echo "Pipeline failed!"
        }

        always {
            echo "Pipeline execution finished."
        }
    }
}
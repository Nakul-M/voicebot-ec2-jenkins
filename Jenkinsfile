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
                python3 -m venv venv
                . venv/bin/activate
                pip install --upgrade pip
                pip install -r requirements.txt
                '''
            }
        }

        stage('Check Ollama Server') {
            steps {
                sh '''
                echo "Checking Ollama server..."
                curl http://172.26.13.25:11434
                '''
            }
        }

        stage('Run Voicebot') {
            steps {
                echo "Starting voicebot..."
                sh '''
                chmod +x scripts/run.sh
                ./scripts/run.sh
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
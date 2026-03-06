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
                sh '''
                set -e

                echo "Python version:"
                python3 --version

                echo "Creating virtual environment..."
                python3 -m venv venv

                echo "Upgrading pip..."
                venv/bin/pip install --upgrade pip

                echo "Installing dependencies..."
                venv/bin/pip install -r requirements.txt
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

        stage('Start Voicebot') {
    steps {
        sh '''
        set -e

        echo "Checking if voicebot already running..."
        ps aux | grep "src/app.py" || true

        echo "Starting voicebot..."

        nohup venv/bin/python src/app.py > app.log 2>&1 &

        echo "Waiting for server..."
        sleep 5

        echo "Running python processes:"
        ps aux | grep python || true

        echo "Checking port 8080..."
        ss -tulnp | grep 8080 || true

        echo "Last logs:"
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
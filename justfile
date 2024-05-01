default:
    setup


setup:
    pdm sync --prod
    cp -n src/bigbunther/.env.example src/bigbunther/.env
    @echo "\nSetup complete. Please edit src/bigbunther/.env to your liking."
    @echo "Then run 'just run' to start the program."

setup-dev:
    pdm sync --dev
    pdm run pre-commit install

run:
    cd src/bigbunther && pdm run main.py

gif:
    cd src/bigbunther && pdm run gif.py 

docker-dev *COMMAND:
    docker compose -f docker-compose.dev.yaml {{COMMAND}}


pre-commit:
    pdm run pre-commit run --all-files

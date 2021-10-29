## Найстрока и запуск приложения

1. Выполнить команду `docker-compose up -d --build`
2. После всей установки можно отправлять GET и POST запросы по адресу `http://0.0.0.0:8000/visited_links/`

## Запуск тестов

`docker exec -it for_funbox_app_1 bash -c ./app/run_tests.sh`
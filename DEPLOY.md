# Настройка CI/CD для RHCSA Testing Service

Этот документ содержит инструкции по настройке автоматического деплоя на удаленную ВМ при коммитах в ветку `main`.

## Настройка GitHub Secrets

Для работы CI/CD вам необходимо настроить следующие секреты в вашем GitHub репозитории:

1. Перейдите в ваш репозиторий на GitHub
2. Откройте вкладку **Settings**
3. В боковом меню выберите **Secrets and variables** → **Actions**
4. Добавьте следующие секреты:

### Обязательные секреты

| Имя секрета | Описание | Пример |
|-------------|----------|--------|
| `SSH_PRIVATE_KEY` | Приватный SSH ключ для доступа к ВМ | `-----BEGIN OPENSSH PRIVATE KEY-----\n...\n-----END OPENSSH PRIVATE KEY-----` |
| `VM_HOST` | IP-адрес или домен удаленной ВМ | `91.107.121.133` или `example.com` |
| `SSH_USER` | Имя пользователя для SSH доступа к ВМ | `deployer` |
| `SSH_PORT` | Порт SSH сервера на удаленной ВМ | `2233` или `22` |
| `PROJECT_PATH` | Путь к проекту на ВМ | `/home/deployer/rhcsa-testing` |

## Настройка удаленной ВМ

1. Создайте пользователя на ВМ (если он еще не создан):
   ```bash
   sudo adduser deployer
   sudo usermod -aG sudo deployer
   ```

2. Настройте SSH доступ (на локальной машине):
   ```bash
   # Генерация SSH ключей, если их еще нет
   ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
   
   # Копирование публичного ключа на сервер
   ssh-copy-id -p 2233 deployer@your_vm_host
   ```

3. Клонирование репозитория на ВМ:
   ```bash
   # Подключитесь к ВМ
   ssh -p 2233 deployer@your_vm_host
   
   # Создайте директорию для проекта и клонируйте репозиторий
   mkdir -p /home/deployer/rhcsa-testing
   cd /home/deployer/rhcsa-testing
   git clone https://github.com/your-username/your-repo.git .
   ```

4. Установите Docker и Docker Compose на ВМ:
   ```bash
   # Установка Docker
   sudo apt-get update
   sudo apt-get install -y docker.io
   
   # Добавление пользователя в группу docker
   sudo usermod -aG docker deployer
   
   # Установка Docker Compose
   sudo apt-get install -y docker-compose-plugin
   ```

5. Настройте беспарольный sudo для команд Docker (необходимо для CI/CD):
   ```bash
   # Откройте sudoers файл
   sudo visudo
   
   # Добавьте строку
   deployer ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/docker compose
   ```

## Проверка деплоя

После настройки всех секретов и подготовки ВМ, каждый пуш в ветку `main` будет автоматически запускать процесс деплоя.

Чтобы проверить работу CI/CD:
1. Внесите изменения в код
2. Закоммитьте и отправьте изменения в ветку `main`:
   ```bash
   git add .
   git commit -m "Test CI/CD deployment"
   git push origin main
   ```
3. Перейдите на GitHub в раздел Actions, чтобы увидеть запущенные workflow
4. После успешного выполнения, приложение будет доступно по адресу http://your_vm_host:8000 
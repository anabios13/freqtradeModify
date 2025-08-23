# 🚀 Быстрый старт FreqTrade Production

## ⚡ За 5 минут от идеи до работающей системы

### 1. На удаленном сервере (Ubuntu/Debian)

```bash
# Подключаемся как root
ssh root@your-server-ip

# Скачиваем и запускаем скрипт настройки
wget https://raw.githubusercontent.com/your-repo/freqtrade/main/deploy/setup-server.sh
chmod +x setup-server.sh
sudo ./setup-server.sh
```

**Скрипт автоматически:**

- ✅ Установит Docker + Docker Compose
- ✅ Создаст пользователя `freqtrader`
- ✅ Настроит Git репозиторий с hooks
- ✅ Создаст все конфиги и docker-compose.yml
- ✅ Настроит systemd сервис
- ✅ Откроет порты в firewall

### 2. На локальной машине

#### Linux/macOS:

```bash
# Делаем скрипт исполняемым
chmod +x deploy/setup-local.sh

# Настраиваем SSH
./deploy/setup-local.sh setup-ssh freqtrader your-server-ip

# Добавляем удаленный репозиторий
./deploy/setup-local.sh add-remote freqtrader your-server-ip
```

#### Windows:

```powershell
# Настраиваем SSH
.\deploy\setup-local.ps1 setup-ssh freqtrader your-server-ip

# Добавляем удаленный репозиторий
.\deploy\setup-local.ps1 add-remote freqtrader your-server-ip
```

### 3. Первый деплой

```bash
# Linux/macOS
./deploy/setup-local.sh deploy

# Windows
.\deploy\setup-local.ps1 deploy
```

**Готово!** 🎉

## 🔄 Ежедневное использование

### Изменили стратегию → Деплой

```bash
# 1. Редактируете код
vim user_data/strategies/Bandtastic.py

# 2. Деплой (автоматически перезапустится только Bandtastic)
./deploy/setup-local.sh deploy
```

### Проверить статус

```bash
# Локально
./deploy/setup-local.sh status freqtrader your-server-ip

# Или на сервере
ssh freqtrader@your-server-ip
sudo /opt/freqtrade/manage.sh status
```

### Просмотр логов

```bash
# Локально
./deploy/setup-local.sh logs freqtrader your-server-ip ft-bandtastic

# Или на сервере
sudo /opt/freqtrade/manage.sh logs ft-bandtastic
```

## 🌐 Доступ к системе

- **Streamlit дашборд**: `http://your-server-ip:8501`
- **SSH доступ**: `ssh freqtrader@your-server-ip`
- **Управление**: `sudo /opt/freqtrade/manage.sh [start|stop|restart|status|logs]`

## 📊 Что запущено

- **6 стратегий** в отдельных Docker контейнерах
- **Изолированные данные** для каждой стратегии
- **Автоматический перезапуск** только измененных стратегий
- **FreqAI обучение** не прерывается при обновлениях
- **Streamlit мониторинг** всех результатов

## 🚨 Если что-то пошло не так

```bash
# Проверить статус
sudo /opt/freqtrade/manage.sh status

# Перезапустить все
sudo /opt/freqtrade/manage.sh restart

# Просмотреть логи
sudo /opt/freqtrade/manage.sh logs

# Проверить логи деплоя
tail -f /opt/freqtrade/deploy.log
```

## 💡 Полезные команды

```bash
# Перезапустить конкретную стратегию
sudo /opt/freqtrade/manage.sh restart ft-bandtastic

# Создать бэкап данных
sudo /opt/freqtrade/manage.sh backup

# Обновить код из Git
sudo /opt/freqtrade/manage.sh update
```

---

**🎯 Цель достигнута: Тестирование стратегий на удаленной машине, редактирование кода локально, автоматический деплой без простоя!**

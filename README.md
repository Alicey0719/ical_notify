# ical_notify
ical diff -> discord webhook


## setup
```
cat <<'EOF' | tee app/.env
ICAL_URL=''
WEBHOOK_URL=''
EOF
```

## run
```
python3 app/ical_notify.py
```
module.exports = {
  apps: [{
    name: 'lec-app',
    script: 'server.py',
    interpreter: 'python3',
    cwd: '/opt/lec-app',
    env: {
      AWS_DEFAULT_REGION: 'us-east-1',
      PYTHONPATH: '/opt/lec-app'
    },
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    error_file: '/var/log/lec-app/err.log',
    out_file: '/var/log/lec-app/out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true
  }]
};

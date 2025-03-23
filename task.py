import csv
import paramiko
import os
import chardet

def detect_encoding(file_path):
    with open(file_path, 'rb') as file:
        raw_data = file.read()
    result = chardet.detect(raw_data)
    return result['encoding']

def read_accounts(file_path):
    encoding = detect_encoding(file_path)
    accounts = []
    with open(file_path, 'r', encoding=encoding) as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # 跳过第一行标题
        for row in reader:
            server_info, username, password, pm2_task, monitor_task = row[:5]
            server, port = server_info.split(':') if ':' in server_info else (server_info, '22')
            accounts.append({
                'server': server,
                'port': int(port),
                'username': username,
                'password': password,
                'pm2_task': pm2_task.lower() == 'true' if pm2_task else False,
                'monitor_task': monitor_task.lower() == 'true' if monitor_task else False
            })
    return accounts

def ssh_connect(host, port, username, password):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, port, username, password, timeout=10)
        return ssh
    except paramiko.AuthenticationException:
        print(f"Authentication failed for {username}@{host}")
    except paramiko.SSHException as ssh_exception:
        print(f"Unable to establish SSH connection: {ssh_exception}")
    except Exception as e:
        print(f"An error occurred: {e}")
    return None

def check_pm2_crontab(ssh, username):
    stdin, stdout, stderr = ssh.exec_command('crontab -l')
    crontab_output = stdout.read().decode('utf-8')
    if 'pm2 resurrect' not in crontab_output:
        print("Adding PM2 resurrect to crontab")
        command = f"echo '@reboot /home/{username}/.npm-global/bin/pm2 resurrect' | crontab -"
        ssh.exec_command(command)

def check_monitor_task(ssh, username):
    sftp = ssh.open_sftp()
    
    # 创建 .bin 目录（如果不存在）
    remote_bin_dir = f'/home/{username}/.bin'
    try:
        sftp.stat(remote_bin_dir)
    except FileNotFoundError:
        print(f"Creating directory {remote_bin_dir}")
        sftp.mkdir(remote_bin_dir)

    remote_path = f'{remote_bin_dir}/monitor.sh'
    
    try:
        sftp.stat(remote_path)
        print("Monitor script already exists")
    except FileNotFoundError:
        print("Monitor script does not exist, uploading...")
        local_path = os.path.join(os.path.dirname(__file__), 'monitor.sh')
        
        # 读取本地monitor.sh文件内容
        with open(local_path, 'r') as local_file:
            content = local_file.read()
        
        # 替换{username}占位符
        modified_content = content.replace('{username}', username)
        
        # 上传修改后的内容
        with sftp.file(remote_path, 'w') as remote_file:
            remote_file.write(modified_content)
        
        sftp.chmod(remote_path, 0o755)

    stdin, stdout, stderr = ssh.exec_command('crontab -l')
    crontab_output = stdout.read().decode('utf-8')
    if remote_path not in crontab_output:
        print("Adding monitor script to crontab")
        command = f"echo '*/5 * * * * {remote_path}' | crontab -"
        ssh.exec_command(command)

def main():
    accounts = read_accounts('accounts.csv')
    for account in accounts:
        ssh = ssh_connect(account['server'], account['port'], account['username'], account['password'])
        if ssh:
            if account['pm2_task']:
                check_pm2_crontab(ssh, account['username'])
            if account['monitor_task']:
                check_monitor_task(ssh, account['username'])
            ssh.close()

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()


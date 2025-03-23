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
        next(reader)  # 跳过标题行
        for row in reader:
            server_info, username, password, pm2_task, monitor_task = row[:5]
            server, port = server_info.split(':') if ':' in server_info else (server_info, '22')
            accounts.append({
                'server': server,
                'port': int(port),
                'username': username,
                'password': password,
                'pm2_task': pm2_task.lower() == 'true',
                'monitor_task': monitor_task.lower() == 'true'
            })
    return accounts

def ssh_connect(host, port, username, password):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, port, username, password, timeout=10)
        return ssh
    except paramiko.AuthenticationException:
        print(f"✗ 认证失败 {username}@{host}")
    except paramiko.SSHException as e:
        print(f"✗ SSH连接失败 {host}: {str(e)}")
    except Exception as e:
        print(f"✗ 连接错误 {host}: {str(e)}")
    return None

def safe_update_crontab(ssh, new_entry):
    # 获取现有crontab
    stdin, stdout, stderr = ssh.exec_command('crontab -l')
    crontab_content = stdout.read().decode().strip()
    errors = stderr.read().decode().strip()

    # 处理没有crontab的情况（忽略正常提示）
    if errors and "no crontab" not in errors.lower():
        print(f"! 读取crontab失败: {errors}")
        return False

    # 检查条目是否已存在
    if new_entry in crontab_content:
        print("√ 任务已存在")
        return True

    # 合并新旧内容
    updated_content = f"{crontab_content}\n{new_entry}" if crontab_content else new_entry

    # 安全写入（使用printf处理特殊字符）
    command = f'printf "%s\\n" "{updated_content}" | crontab -'
    stdin, stdout, stderr = ssh.exec_command(command)
    
    # 验证结果
    error = stderr.read().decode().strip()
    if error:
        print(f"! 写入失败: {error}")
        return False
    
    print("√ 任务添加成功")
    return True

def check_pm2_crontab(ssh, username):
    pm2_path = f'/home/{username}/.npm-global/bin/pm2'
    
    # 验证pm2路径
    stdin, stdout, stderr = ssh.exec_command(f'ls {pm2_path}')
    if stderr.read().decode().strip():
        print(f"! PM2路径不存在: {pm2_path}")
        return

    new_entry = f'@reboot {pm2_path} resurrect'
    print(f"正在处理PM2任务: {new_entry}")
    return safe_update_crontab(ssh, new_entry)

def check_monitor_task(ssh, username):
    sftp = ssh.open_sftp()
    remote_dir = f'/home/{username}/.bin'
    remote_path = f'{remote_dir}/monitor.sh'

    try:
        sftp.stat(remote_dir)
    except FileNotFoundError:
        print(f"创建目录 {remote_dir}")
        sftp.mkdir(remote_dir)

    # 上传/更新监控脚本
    try:
        local_path = os.path.join(os.path.dirname(__file__), 'monitor.sh')
        with open(local_path, 'r') as f:
            content = f.read().replace('{username}', username)

        with sftp.file(remote_path, 'w') as remote_file:
            remote_file.write(content)
        
        sftp.chmod(remote_path, 0o755)
        print("√ 监控脚本已更新")
    except Exception as e:
        print(f"! 脚本上传失败: {str(e)}")
        return

    new_entry = f'*/5 * * * * {remote_path}'
    print(f"正在处理监控任务: {new_entry}")
    return safe_update_crontab(ssh, new_entry)

def main():
    accounts = read_accounts('accounts.csv')
    for acc in accounts:
        print(f"\n=== 处理 {acc['username']}@{acc['server']}:{acc['port']} ===")
        ssh = ssh_connect(acc['server'], acc['port'], acc['username'], acc['password'])
        if not ssh:
            continue

        try:
            if acc['pm2_task']:
                check_pm2_crontab(ssh, acc['username'])
            if acc['monitor_task']:
                check_monitor_task(ssh, acc['username'])
        finally:
            ssh.close()

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()


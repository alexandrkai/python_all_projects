# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/core/subprocess_timeout.py
import asyncio
import subprocess
from typing import Optional, Dict, Any
from config.config import Config
from datetime import datetime
from log.log import logger

async def run_subprocess_with_timeout_async(
    command: list[str],
    timeout_seconds: int,
    cwd: Optional[str] = None,
    env: Optional[dict] = None
) -> tuple[int, str, str]:
    """Запускает субпроцесс с таймаутом"""
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds
            )
            
            return_code = process.returncode
            
            stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ''
            stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ''
            
            if return_code != 0:
                raise subprocess.CalledProcessError(
                    return_code, 
                    command, 
                    stdout_str, 
                    stderr_str
                )
                
            return return_code, stdout_str, stderr_str
            
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise asyncio.TimeoutError(
                f"Процесс {command} превысил таймаут {timeout_seconds} секунд"
            )
            
    except Exception as e:
        raise

async def run_process(command: list[str], timeout: int = 30) -> Dict[str, Any]:
    """Запуск процесса через API с таймаутом"""
    result = {
        "sender": Config.SENDER,
        "due_date": datetime.now().isoformat()
    }
    
    try:
        print(f"Выполняем команду {command}")
        return_code, stdout, stderr = await run_subprocess_with_timeout_async(
            command=command,
            timeout_seconds=timeout
        )
        
        result.update({
            "success": "ok",
            "return_code": return_code,
            "data": stdout,
            "stdout": stdout,
            "stderr": stderr,
            "message": "Процесс успешно завершен",
            "status": "success"
        })
        
    except asyncio.TimeoutError as e:
        mess = "⚠️"+str(e)
        logger.error(mess)
        result.update({
            "message": "Процесс превысил таймаут",
            "status": "error",
            "detail": f"Таймаут: {mess}",
            "success": "error",
            "return_code": -1,
            "data": "",
            "stdout": "",
            "stderr": mess
        })
        
    except subprocess.CalledProcessError as e:
        mess = "⚠️"+str(e)
        logger.error(mess)
        result.update({
            "message": "Процесс завершился с ошибкой",
            "status": "error",
            "return_code": e.returncode,
            "stdout": e.stdout,
            "stderr": e.stderr,
            "detail": f"Ошибка процесса: {mess}",
            "success": "error",
            "data": ""
        })
        
    except Exception as e:
        mess = str(e)
        logger.error(f"⚠️Неожиданная ошибка: {mess}")
        result.update({
            "message": "Неожиданная ошибка",
            "status": "error",
            "detail": f"Ошибка: {mess}",
            "success": "error",
            "return_code": -1,
            "data": "",
            "stdout": "",
            "stderr": mess
        })
    
    return result  # ✅ Возвращаем dict, а не корутину
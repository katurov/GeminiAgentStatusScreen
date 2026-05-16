use std::env;
use std::io::{self, Read, Write};
use std::net::{TcpStream, SocketAddr, ToSocketAddrs};
use std::time::Duration;

#[cfg(unix)]
extern "C" {
    fn getppid() -> i32;
}

#[cfg(not(unix))]
unsafe fn getppid() -> i32 {
    0
}

fn redis_lpush_raw(host: &str, port: u16, queue: &str, data_str: &str) -> bool {
    let cmd = format!(
        "*3\r\n$5\r\nLPUSH\r\n${}\r\n{}\r\n${}\r\n{}\r\n",
        queue.len(), queue, data_str.len(), data_str
    );

    let addr_str = format!("{}:{}", host, port);
    let addrs: Vec<SocketAddr> = match addr_str.to_socket_addrs() {
        Ok(iter) => iter.collect(),
        Err(_) => return false,
    };

    for addr in addrs {
        // Устанавливаем короткий таймаут в 50мс, как в Python скрипте
        if let Ok(mut stream) = TcpStream::connect_timeout(&addr, Duration::from_millis(50)) {
            let _ = stream.set_write_timeout(Some(Duration::from_millis(50)));
            if stream.write_all(cmd.as_bytes()).is_ok() {
                return true;
            }
        }
    }
    false
}

fn main() {
    // Пытаемся загрузить .env переменные (поиск идет от текущей папки и выше)
    let _ = dotenvy::dotenv();

    let mut input_data = String::new();
    if io::stdin().read_to_string(&mut input_data).is_err() || input_data.trim().is_empty() {
        return;
    }

    let payload = match serde_json::from_str::<serde_json::Value>(&input_data) {
        Ok(mut data) => {
            if let Some(obj) = data.as_object_mut() {
                let ppid = unsafe { getppid() };
                obj.insert("_ppid".to_string(), serde_json::Value::Number(ppid.into()));
            }
            serde_json::to_string(&data).unwrap_or(input_data.clone())
        }
        Err(_) => input_data, // Фолбек, если это не валидный JSON
    };

    let r_host = env::var("REDIS_HOST").unwrap_or_else(|_| "127.0.0.1".to_string());
    let r_port: u16 = env::var("REDIS_PORT")
        .unwrap_or_else(|_| "6379".to_string())
        .parse()
        .unwrap_or(6379);
    let r_queue = env::var("REDIS_QUEUE").unwrap_or_else(|_| "gemini_events".to_string());

    redis_lpush_raw(&r_host, r_port, &r_queue, &payload);

    // Отвечаем Gemini CLI пустым JSON
    print!("{{}}");
    let _ = io::stdout().flush();
}

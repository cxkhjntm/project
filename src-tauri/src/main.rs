// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::api::process::{Command, CommandEvent};
use tauri::Manager;
use log::{info, error};

struct BackendState {
    child: Option<tauri::api::process::CommandChild>,
}

fn start_backend(app: &tauri::App) -> Result<(), String> {
    let sidecar = Command::new_sidecar("expert-room-backend")
        .map_err(|e| format!("Failed to create sidecar command: {}", e))?;

    let (mut rx, child) = sidecar
        .spawn()
        .map_err(|e| format!("Failed to spawn backend sidecar: {}", e))?;

    app.manage(BackendState {
        child: Some(child),
    });

    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    info!("[Backend] {}", line);
                }
                CommandEvent::Stderr(line) => {
                    info!("[Backend] {}", line);
                }
                CommandEvent::Terminated(status) => {
                    error!("[Backend] Process terminated with status: {:?}", status);
                    break;
                }
                _ => {}
            }
        }
    });

    info!("Backend sidecar started successfully");
    Ok(())
}

#[tauri::command]
async fn check_backend_health() -> Result<bool, String> {
    let client = reqwest::Client::new();
    match client
        .get("http://127.0.0.1:8000/api/health")
        .timeout(std::time::Duration::from_secs(2))
        .send()
        .await
    {
        Ok(resp) => Ok(resp.status().is_success()),
        Err(_) => Ok(false),
    }
}

#[tauri::command]
fn get_app_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

fn main() {
    env_logger::init();

    tauri::Builder::default()
        .setup(|app| {
            info!("Initializing Expert Room application...");

            if let Err(e) = start_backend(app) {
                error!("Failed to start backend: {}", e);
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            check_backend_health,
            get_app_version,
        ])
        .on_window_event(|event| match event.event() {
            tauri::WindowEvent::CloseRequested { .. } => {
                let app_handle = event.window().app_handle();

                if let Some(state) = app_handle.try_state::<BackendState>() {
                    if let Some(child) = &state.child {
                        if let Err(e) = child.kill() {
                            error!("Failed to kill backend process: {}", e);
                        }
                    }
                }

                info!("Application closing");
            }
            _ => {}
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

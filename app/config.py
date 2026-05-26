class DefaultConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    APP_NAME = "Al-Salat Al-Muhammadiya & Al-Salat Al-Ibrahimiya"
    SUPPORTED_LANGS = ("ar", "en", "ku")
    DEFAULT_LANG = "ar"
    

    SECRET_KEY = "super-secret-key-for-al-salat-app-2026" 
    SESSION_COOKIE_SECURE = False      
    SESSION_COOKIE_HTTPONLY = True     
    SESSION_COOKIE_SAMESITE = 'Lax'    

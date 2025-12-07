import os

def main():
    password = os.getenv("LOGIN_PASSWORD", "admin123")
    print(f"Default login password: {password}")
    print("Change it by setting LOGIN_PASSWORD in .env file")

if __name__ == "__main__":
    main()
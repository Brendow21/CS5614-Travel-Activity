# CS5614-Travel-Activity

# 🌍 Travel Buddy Finder — Local Development Guide

This guide provides everything you need to run the Travel Buddy Finder application locally, including installation, setup, environment configuration, and running the development server.

---

## 📦 Project Overview

Travel Buddy Finder is a full-stack Django web application that helps users discover travel destinations, create trips, and connect with others who share similar travel interests.  
The application includes user authentication, trip drafting, activity search (via Google Places API), and a personalized profile page.

---

# 🚀 Running the Project Locally

### **1. Clone the repository**

### **2. Create a virtual environment**
- python -m venv .venv

### **3. Activate  virtual environment**
- source .venv/bin/Activate.ps1   (macOS/Linux)
- .venv\Scripts\Activate.ps1      (Windows)

### **4. Install dependencies**
- pip install -r requirements.txt\

### **5. Set up Environment Variables**
- In the .env.placeholder, rename to .env
- Add in Google Places API key

### **6. Change folder to be in this path**
- CS5614-TravelActivity/travel-activity

### **7. Run Migrations**
- python manage.py migrate

### **8. Run Locally**
- python manage.py runserver

---
import os
import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

try:
    from google import genai
    from google.genai import types
except ImportError:
    raise ImportError("Please install the modern Google GenAI SDK: pip install google-genai")

app = FastAPI()

# --- INITIALIZE COGNITIVE GENAI CLIENT ---
client = genai.Client(api_key="AQ.Ab8RN6LWcCGMz7sWf0sHJ3h5zEDKhBFpzh-bWkgGCUEe6ZlY9A")

# Mock Database Structure indexed by Profile Name
USER_DB: Dict[str, dict] = {
    "aosaf": {
        "password": "password123",
        "q1": "What was the name of your very first childhood pet?", "a1": "buddy",
        "q2": "What is your preferred absolute favorite food dish?", "a2": "biryani"
    }
}
HISTORY_DB = []  

class UserAuth(BaseModel):
    profile_name: str
    password: str
    question1: Optional[str] = None
    answer1: Optional[str] = None
    question2: Optional[str] = None
    answer2: Optional[str] = None

class PasswordRecoveryVerify(BaseModel):
    profile_name: str
    answer1: str
    answer2: str

class PasswordUpdate(BaseModel):
    profile_name: str
    old_password: str
    new_password: str

class SecurityQuestionsUpdate(BaseModel):
    profile_name: str
    password_validation: str
    question1: str
    answer1: str
    question2: str
    answer2: str

# --- STRUCTURAL ENFORCEMENT SCHEMAS ---
class PathwayStep(BaseModel):
    title: str = Field(description="Title of this phase of the career roadmap.")
    details: str = Field(description="Specific, actionable steps, skills, or certifications to acquire.")
    duration: str = Field(description="Estimated time to complete this step (e.g., '3 months', 'Continuous').")

class InterviewPrepItem(BaseModel):
    question: str = Field(description="High-yield behavior or technical interview/audition question specific to this role.")
    optimal_response_strategy: str = Field(description="Step-by-step psychological or technical breakdown of how to ace the answer.")

class UniversalRoadmapResponse(BaseModel):
    target_job: str = Field(description="The formal title of the target job requested by the user.")
    reality_check: str = Field(description="An honest, grounded industry summary detailing the true entry barriers or expectations of this market space.")
    timeline_duration: str = Field(description="Total estimated timeline length (e.g., '1-2 years').")
    core_subjects: List[str] = Field(description="Top 3-4 core technical/artistic fundamentals or absolute legal requirements.")
    supporting_skills: List[str] = Field(description="Top 3-4 secondary soft skills or cross-disciplinary capabilities.")
    standout_extras: List[str] = Field(description="Top 2-3 impressive elements like portfolios, specific guilds, or high-tier certifications.")
    pathway: List[PathwayStep] = Field(description="A chronologically ordered roadmap breaking down the execution path.")
    interview_prep: List[InterviewPrepItem] = Field(description="At least 3-5 comprehensive interview preparation drills.")


# --- FRONTEND INTERFACE ---
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CareerLens — Universal AI Career Advisor</title>
    <style>
        :root[data-theme="dark"] { 
            --bg-main: #121214; 
            --bg-card: #1a1a1e; 
            --bg-input: #252529;
            --border: #2d2d34;
            --text-main: #e0e0e6; 
            --text-strong: #ffffff;
            --text-muted: #aaa;
            --primary: #5c6bc0; 
            --badge-core-bg: #5c1d1d; --badge-core-txt: #ff9999;
            --badge-support-bg: #5c531d; --badge-support-txt: #ffeb99;
            --badge-extra-bg: #1d5c3a; --badge-extra-txt: #99ffc2;
            --pill-bg: #232329; --pill-txt: #b0bec5;
        }
        
        :root[data-theme="light"] { 
            --bg-main: #f4f5f7; 
            --bg-card: #ffffff; 
            --bg-input: #ffffff;
            --border: #dcdce2;
            --text-main: #1c1c1f; 
            --text-strong: #121214;
            --text-muted: #62626a;
            --primary: #3f51b5; 
            --badge-core-bg: #ffebee; --badge-core-txt: #c62828;
            --badge-support-bg: #fffde7; --badge-support-txt: #f57f17;
            --badge-extra-bg: #e8f5e9; --badge-extra-txt: #2e7d32;
            --pill-bg: #eef0f5; --pill-txt: #455a64;
        }
        
        body { 
            font-family: system-ui, sans-serif; 
            margin: 0; 
            background: var(--bg-main); 
            color: var(--text-main); 
            display: flex; 
            flex-direction: row;
            min-height: 100vh; 
            transition: background 0.3s, color 0.3s;
        }
        
        .sidebar { 
            width: 240px; 
            background: var(--bg-card); 
            padding: 20px; 
            display: flex; 
            flex-direction: column; 
            justify-content: space-between; 
            border-right: 1px solid var(--border); 
            flex-shrink: 0;
        }
        .logo { font-size: 20px; font-weight: bold; color: var(--text-strong); margin-bottom: 40px; }
        .nav-links { display: flex; flex-direction: column; gap: 15px; }
        .nav-item { background: none; border: none; color: var(--text-muted); text-align: left; padding: 12px; font-size: 16px; cursor: pointer; border-radius: 6px; width: 100%; transition: 0.2s; display: flex; align-items: center; gap: 10px; }
        .nav-item:hover, .nav-item.active { background: var(--bg-main); color: var(--text-main); }
        .user-profile { border-top: 1px solid var(--border); padding-top: 15px; margin-bottom: 15px; }
        
        .main-wrapper { flex: 1; display: flex; flex-direction: column; width: 100%; box-sizing: border-box; }
        .main-content { flex: 1; padding: 40px; width: 100%; box-sizing: border-box; max-width: 900px; margin: 0 auto; }
        
        .top-toolbar { display: flex; justify-content: flex-end; padding: 15px 40px 0 40px; }
        .theme-btn { background: var(--bg-card); border: 1px solid var(--border); color: var(--text-main); padding: 8px 14px; border-radius: 20px; cursor: pointer; font-size: 14px; }
        
        .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }
        .stat-card { background: var(--bg-card); padding: 20px; border-radius: 8px; text-align: center; border: 1px solid var(--border); }
        .stat-val { font-size: 28px; font-weight: bold; color: var(--text-strong); }
        
        .dashboard-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-top: 30px; }
        .dashboard-card { background: var(--bg-card); padding: 25px; border-radius: 8px; border: 1px solid var(--border); }
        
        .badge-group { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0 20px 0; }
        .badge { padding: 6px 12px; border-radius: 4px; font-size: 13px; font-weight: bold; }
        .badge.core { background: var(--badge-core-bg); color: var(--badge-core-txt); }
        .badge.support { background: var(--badge-support-bg); color: var(--badge-support-txt); }
        .badge.extra { background: var(--badge-extra-bg); color: var(--badge-extra-txt); }
        
        .timeline-item { position: relative; padding-left: 35px; margin-bottom: 25px; }
        .timeline-num { position: absolute; left: 0; top: 2px; width: 22px; height: 22px; background: var(--primary); color: white; border-radius: 50%; text-align: center; font-size: 12px; line-height: 22px; font-weight: bold; }
        
        textarea, input, select { width: 100%; padding: 12px; background: var(--bg-input); border: 1px solid var(--border); color: var(--text-main); border-radius: 6px; box-sizing: border-box; margin-bottom: 15px; font-size: 15px; }
        select { cursor: pointer; }
        
        .input-hint { font-size: 11px; color: var(--text-muted); display: block; margin-top: -12px; margin-bottom: 12px; padding-left: 2px; }
        .input-label { font-size: 13px; font-weight: 600; color: var(--text-main); display: block; margin-bottom: 6px; }

        .password-container { position: relative; width: 100%; }
        .toggle-password { position: absolute; right: 12px; top: 12px; background: none; border: none; color: var(--text-muted); cursor: pointer; }
        .submit-btn { background: var(--primary); color: white; border: none; padding: 14px; width: 100%; border-radius: 6px; font-size: 16px; cursor: pointer; font-weight: bold; margin-bottom: 10px; }
        .submit-btn:disabled { background: var(--border); color: var(--text-muted); cursor: not-allowed; }
        
        .history-table { width: 100%; border-collapse: collapse; background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; margin-top: 15px; }
        .history-table th, .history-table td { padding: 14px; text-align: left; border-bottom: 1px solid var(--border); }
        .history-table th { background: var(--bg-input); color: var(--text-strong); font-weight: 600; }
        
        .clickable-row { cursor: pointer; transition: background 0.2s; }
        .clickable-row:hover { background: var(--bg-input); }
        
        .delete-btn { background: none; border: none; color: #ff4d4d; font-size: 16px; cursor: pointer; padding: 5px 10px; border-radius: 4px; transition: background 0.2s; }
        .delete-btn:hover { background: rgba(255, 77, 77, 0.15); }
        
        .secondary-link { display: block; text-align: center; color: var(--primary); text-decoration: none; font-size: 14px; cursor: pointer; margin-top: 5px; }
        .secondary-link:hover { text-decoration: underline; }

        .about-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; padding: 40px 20px; text-align: center; margin-bottom: 25px; }
        .avatar-circle { width: 90px; height: 90px; background: var(--primary); color: white; font-size: 36px; font-weight: bold; display: flex; align-items: center; justify-content: center; border-radius: 50%; margin: 0 auto 20px auto; }
        .creator-name { font-size: 28px; font-weight: 800; margin: 0 0 8px 0; color: var(--text-strong); }
        .creator-inst { font-size: 16px; color: var(--primary); font-weight: 600; margin-bottom: 4px; }
        .about-badge-group { display: flex; justify-content: center; flex-wrap: wrap; gap: 12px; margin-top: 15px; }
        .about-tag { padding: 8px 18px; border-radius: 20px; font-size: 13px; font-weight: 600; }
        .about-tag.buet { background: rgba(92, 107, 192, 0.15); color: var(--primary); }
        .about-tag.dev { background: rgba(46, 125, 50, 0.15); color: #2e7d32; }
        .about-tag.ai { background: rgba(255, 179, 0, 0.15); color: #f57f17; }

        @media (max-width: 900px) {
            body { flex-direction: column; }
            .sidebar { width: 100%; border-right: none; border-bottom: 1px solid var(--border); }
            .nav-links { flex-direction: row; flex-wrap: wrap; gap: 10px; }
            .dashboard-grid { grid-template-columns: 1fr; }
            .stats-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>

    <!-- SIDEBAR -->
    <div class="sidebar">
        <div>
            <div class="logo">Career<span style="color:var(--primary)">.lens</span> ☀️</div>
            <div class="nav-links">
                <button class="nav-item" id="menuAnalyze" onclick="setView('analyze')">🔍 Analyze</button>
                <button class="nav-item" id="menuInterview" onclick="setView('interview')">👔 Interview Prep</button>
                <button class="nav-item" id="menuHistory" onclick="setView('history')">📁 History</button>
                <button class="nav-item" id="menuProfile" onclick="setView('profile')">👤 My Profile</button>
                <button class="nav-item" id="menuAbout" onclick="setView('about')">ℹ️ About</button>
            </div>
        </div>
        <div>
            <div class="user-profile" id="userProfileArea" style="display:none;">
                <div style="font-size:14px; font-weight:bold;" id="profileDisplayTag">User</div>
                <div style="font-size:12px; color:var(--text-muted); margin-bottom:10px;">BUET EEE Student</div>
                <button style="background:none; border:none; color:#ff4d4d; padding:0; cursor:pointer;" onclick="logout()">Logout &rarr;</button>
            </div>
        </div>
    </div>

    <!-- MAIN WRAPPER -->
    <div class="main-wrapper">
        <div class="top-toolbar">
            <button class="theme-btn" onclick="toggleTheme()" id="themeBtn">☀️ Bright Mode</button>
        </div>

        <div class="main-content">
            
            <!-- AUTH PORTAL -->
            <div id="authView" style="max-width: 400px; margin: 40px auto; background: var(--bg-card); padding: 30px; border-radius: 8px; border:1px solid var(--border);">
                <div id="authFormTitle"><h3>Sign In / Register</h3></div>
                
                <label class="input-label" for="authProfileName" id="profileLabel">Account Profile Name:</label>
                <input type="text" id="authProfileName" placeholder="Enter alphanumeric unique username (lowercase)" value="aosaf">
                <span class="input-hint" id="profileHint">Must be a single, continuous word with no spaces or special symbols.</span>
                
                <label class="input-label" for="authPassword">Account Password:</label>
                <div class="password-container" style="margin-bottom: 15px;">
                    <input type="password" id="authPassword" placeholder="Enter secure personal password credentials" value="password123" style="margin-bottom:0;">
                    <button type="button" class="toggle-password" onclick="togglePasswordVisibility('authPassword', 'eyeBtn')" id="eyeBtn">👁️ Show</button>
                </div>
                <span class="input-hint">Min. 6 characters. Kept fully encrypted in transient memory.</span>

                <!-- SECURITY QUESTIONS FIELDS -->
                <div id="securityQuestionsFields" style="display:none; border-top: 1px solid var(--border); padding-top:15px; margin-top:10px;">
                    <label style="font-size:13px; color:var(--text-muted); display:block; margin-bottom:5px;">Security Verification Question 1:</label>
                    <select id="regQ1">
                        <option value="What was the name of your very first childhood pet?">What was the name of your very first childhood pet?</option>
                        <option value="In what city or town did your parents meet?">In what city or town did your parents meet?</option>
                        <option value="What was the model of your first car or vehicle?">What was the model of your first car or vehicle?</option>
                    </select>
                    <input type="text" id="regA1" placeholder="Provide answer value here">

                    <label style="font-size:13px; color:var(--text-muted); display:block; margin-bottom:5px;">Security Verification Question 2:</label>
                    <select id="regQ2">
                        <option value="What was the name of your elementary primary school?">What was the name of your elementary primary school?</option>
                        <option value="What is your preferred absolute favorite food dish?">What is your preferred absolute favorite food dish?</option>
                        <option value="What was the first music concert you attended?">What was the first music concert you attended?</option>
                    </select>
                    <input type="text" id="regA2" placeholder="Provide answer value here">
                </div>

                <div id="authActions">
                    <button class="submit-btn" onclick="handleAuth('/api/login')">Login</button>
                    <button class="secondary-link" onclick="toggleRegisterMode(true)">New here? Create Account with Security Questions</button>
                    <button class="secondary-link" onclick="switchToForgotView()">Forgot Password?</button>
                </div>
            </div>

            <!-- FORGOT PASSWORD VERIFICATION VIEW -->
            <div id="forgotView" style="display: none; max-width: 400px; margin: 40px auto; background: var(--bg-card); padding: 30px; border-radius: 8px; border:1px solid var(--border);">
                <h3>Recover Password</h3>
                <p style="font-size:13px; color:var(--text-muted); margin-bottom:15px;">Provide your Profile Name to fetch your security challenge verification prompts.</p>
                
                <label class="input-label" for="forgotProfileName">Target Profile Name:</label>
                <input type="text" id="forgotProfileName" placeholder="Type your lowercase unique profile name">
                <button class="submit-btn" id="fetchQuestionsBtn" onclick="fetchUserQuestions()">Fetch Challenge Questions</button>

                <div id="challengeContainer" style="display:none; margin-top:15px; border-top:1px solid var(--border); padding-top:15px;">
                    <div id="challengePrompt1" style="font-weight:bold; font-size:14px; margin-bottom:5px; color:var(--text-strong);">Question 1</div>
                    <input type="text" id="challengeAns1" placeholder="Type Answer 1 matching your profile save state">

                    <div id="challengePrompt2" style="font-weight:bold; font-size:14px; margin-bottom:5px; color:var(--text-strong);">Question 2</div>
                    <input type="text" id="challengeAns2" placeholder="Type Answer 2 matching your profile save state">

                    <button class="submit-btn" style="background:#2e7d32;" onclick="verifyRecoveryChallenge()">Verify & Reveal Password</button>
                </div>

                <button class="secondary-link" onclick="switchToLoginView()">&larr; Return to Sign In</button>
            </div>

            <!-- ANALYZE INTERFACE -->
            <div id="analyzeView" style="display: none;">
                <h2>AI Universal Career Advisor</h2>
                <p style="color:var(--text-muted);">Type **absolutely any occupation** in existence—from traditional corporate to ultra-niche domains.</p>
                
                <input type="text" id="targetJob" placeholder="e.g., Actress, Astronaut, Deep Sea Diver...">
                <label style="display:block; margin-bottom:5px;">Upload CV (PDF - Optional):</label>
                <input type="file" id="cvFile" accept=".pdf">
                <button class="submit-btn" id="analyzeBtn" onclick="runAnalysis()">Analyze & Generate Roadmap</button>

                <!-- OUTPUT DASHBOARD -->
                <div id="resultDashboard" style="display: none; margin-top:40px;">
                    <div style="background:rgba(92, 107, 192, 0.15); color:var(--primary); padding: 15px; border-radius: 6px; margin-bottom: 20px; font-weight:500; border: 1px solid var(--border);" id="realityCheck"></div>
                    
                    <div class="stats-grid">
                        <div class="stat-card"><div class="stat-val" id="statSubjects">0</div><div style="color:var(--text-muted); font-size:14px; margin-top:4px;">focus areas</div></div>
                        <div class="stat-card"><div class="stat-val" id="statStages">0</div><div style="color:var(--text-muted); font-size:14px; margin-top:4px;">milestones</div></div>
                        <div class="stat-card"><div class="stat-val" id="statYears">0</div><div style="color:var(--text-muted); font-size:14px; margin-top:4px;">timeline scope</div></div>
                    </div>

                    <div class="dashboard-grid">
                        <div class="dashboard-card">
                            <h3 style="margin-top:0; color:var(--text-strong);">🛠️ Focus & Competencies</h3>
                            <div style="margin-top:15px;"><strong>Core Requirements</strong></div><div class="badge-group" id="groupCore"></div>
                            <div style="margin-top:15px;"><strong>Supporting Capabilities</strong></div><div class="badge-group" id="groupSupport"></div>
                            <div style="margin-top:15px;"><strong>Stand-out Extras</strong></div><div class="badge-group" id="groupExtra"></div>
                        </div>
                        <div class="dashboard-card">
                            <h3 style="margin-top:0; color:var(--text-strong);">🗺️ Custom Career Pathway</h3>
                            <div id="pathwayTimeline" style="margin-top:20px;"></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- INTERVIEW PREP -->
            <div id="interviewView" style="display: none;">
                <h2>Tailored Industry Evaluation Strategy</h2>
                <p style="color:var(--text-muted); margin-bottom: 20px;">Review customized vetting scenarios generated dynamically by the AI framework engine.</p>
                <div id="interviewContainer">
                    <p style="color:var(--text-muted);">Run a dynamic advisor analysis to instantly populate structural test scenarios.</p>
                </div>
            </div>

            <!-- HISTORY PANEL -->
            <div id="historyView" style="display: none;">
                <h2>Analysis History Log</h2>
                <p style="color:var(--text-muted); margin-bottom: 5px;">Click any row to reload that specific roadmap profile, or use the trash icon to delete it permanently.</p>
                <table class="history-table">
                    <thead>
                        <tr>
                            <th>Date Timestamp</th>
                            <th>Target Intent Profile</th>
                            <th style="width: 100px; text-align: center;">Actions</th>
                        </tr>
                    </thead>
                    <tbody id="historyTableBody"></tbody>
                </table>
            </div>

            <!-- DYNAMIC USER PROFILE SECTION -->
            <div id="profileView" style="display: none;">
                <h2>Account Settings</h2>
                <p style="color:var(--text-muted); margin-bottom: 25px;">Manage security keys and check infrastructure profile parameters.</p>
                
                <div class="dashboard-card" style="margin-bottom: 25px;">
                    <h3 style="margin-top:0; color:var(--text-strong);">Profile Overview</h3>
                    <div style="margin-bottom: 12px;">
                        <span style="color:var(--text-muted); font-size:14px;">Active Profile Name:</span>
                        <div style="font-size:20px; font-weight:bold; color:var(--primary); margin-top:4px;" id="profileSettingName">---</div>
                    </div>
                    <div>
                        <span style="color:var(--text-muted); font-size:14px;">Institutional Access Tier:</span>
                        <div style="font-size:15px; margin-top:4px; color:var(--text-strong);">BUET EEE Engineering Student Node</div>
                    </div>
                </div>

                <!-- NEW COMPONENT: SECURITY QUESTIONS MANAGEMENT -->
                <div class="dashboard-card" style="margin-bottom: 25px;">
                    <h3 style="margin-top:0; color:var(--text-strong); margin-bottom:20px;">🛡️ Update Security Challenge Configuration</h3>
                    
                    <label class="input-label">Select Security Question 1:</label>
                    <select id="profileQ1">
                        <option value="What was the name of your very first childhood pet?">What was the name of your very first childhood pet?</option>
                        <option value="In what city or town did your parents meet?">In what city or town did your parents meet?</option>
                        <option value="What was the model of your first car or vehicle?">What was the model of your first car or vehicle?</option>
                    </select>
                    
                    <label class="input-label">New Answer 1:</label>
                    <div class="password-container" style="margin-bottom: 15px;">
                        <input type="password" id="profileA1" placeholder="Type new answer 1 verification value" style="margin-bottom:0;">
                        <button type="button" class="toggle-password" onclick="togglePasswordVisibility('profileA1', 'a1EyeBtn')" id="a1EyeBtn">👁️ Show</button>
                    </div>

                    <label class="input-label">Select Security Question 2:</label>
                    <select id="profileQ2">
                        <option value="What was the name of your elementary primary school?">What was the name of your elementary primary school?</option>
                        <option value="What is your preferred absolute favorite food dish?">What is your preferred absolute favorite food dish?</option>
                        <option value="What was the first music concert you attended?">What was the first music concert you attended?</option>
                    </select>
                    
                    <label class="input-label">New Answer 2:</label>
                    <div class="password-container" style="margin-bottom: 15px;">
                        <input type="password" id="profileA2" placeholder="Type new answer 2 verification value" style="margin-bottom:0;">
                        <button type="button" class="toggle-password" onclick="togglePasswordVisibility('profileA2', 'a2EyeBtn')" id="a2EyeBtn">👁️ Show</button>
                    </div>

                    <label class="input-label" style="border-top: 1px solid var(--border); padding-top:15px; margin-top:15px;">Confirm Account Password:</label>
                    <div class="password-container">
                        <input type="password" id="profileSecurityConfirmPass" placeholder="Verify password to update security parameters">
                        <button type="button" class="toggle-password" onclick="togglePasswordVisibility('profileSecurityConfirmPass', 'secConfirmEyeBtn')" id="secConfirmEyeBtn">👁️ Show</button>
                    </div>

                    <button class="submit-btn" style="margin-top:10px; background:#2e7d32;" onclick="updateSecurityQuestions()">Synchronize Security Questions</button>
                </div>

                <div class="dashboard-card">
                    <h3 style="margin-top:0; color:var(--text-strong); margin-bottom:20px;">🔒 Modify Account Password</h3>
                    
                    <label class="input-label">Current Active Password:</label>
                    <div class="password-container">
                        <input type="password" id="profileOldPass" placeholder="Type current password validation token">
                        <button type="button" class="toggle-password" onclick="togglePasswordVisibility('profileOldPass', 'oldEyeBtn')" id="oldEyeBtn">👁️ Show</button>
                    </div>

                    <label class="input-label">New Password:</label>
                    <div class="password-container">
                        <input type="password" id="profileNewPass" placeholder="Type target secure password configuration">
                        <button type="button" class="toggle-password" onclick="togglePasswordVisibility('profileNewPass', 'newEyeBtn')" id="newEyeBtn">👁️ Show</button>
                    </div>
                    <span class="input-hint">Must be at least 6 characters in length.</span>

                    <button class="submit-btn" style="margin-top:10px;" onclick="updateUserPassword()">Apply New Password</button>
                </div>
            </div>

            <!-- ABOUT VIEW -->
            <div id="aboutView" style="display: none;">
                <div class="about-card">
                    <div class="avatar-circle">A</div>
                    <h1 class="creator-name">Aosaf Ahbab Rayeed</h1>
                    <div class="creator-inst">Bangladesh University of Engineering & Technology</div>
                    <div style="font-size:14px; color:var(--text-muted); margin-bottom:25px;">Department of Electrical & Electronic Engineering (EEE)</div>
                    <div class="about-badge-group">
                        <span class="about-tag buet">🎓 BUET EEE</span>
                        <span class="about-tag dev">⚡ Engineer & Developer</span>
                        <span class="about-tag ai">🤖 Real AI Integration</span>
                    </div>
                </div>
            </div>

        </div>
    </div>

    <script>
        let currentUser = localStorage.getItem('profileName') || "";
        let isRegisterMode = false;

        function setView(view) {
            if(!currentUser && view !== 'about') {
                alert("Access Denied: Please authenticate via the Sign In portal to use CareerLens Advisor tools.");
                return;
            }

            document.getElementById('analyzeView').style.display = view === 'analyze' ? 'block' : 'none';
            document.getElementById('interviewView').style.display = view === 'interview' ? 'block' : 'none';
            document.getElementById('historyView').style.display = view === 'history' ? 'block' : 'none';
            document.getElementById('profileView').style.display = view === 'profile' ? 'block' : 'none';
            document.getElementById('aboutView').style.display = view === 'about' ? 'block' : 'none';
            
            document.getElementById('menuAnalyze').classList.toggle('active', view === 'analyze');
            document.getElementById('menuInterview').classList.toggle('active', view === 'interview');
            document.getElementById('menuHistory').classList.toggle('active', view === 'history');
            document.getElementById('menuProfile').classList.toggle('active', view === 'profile');
            document.getElementById('menuAbout').classList.toggle('active', view === 'about');

            if(view === 'history') loadHistoryLogs();
            if(view === 'profile') {
                document.getElementById('profileSettingName').innerText = currentUser;
                document.getElementById('profileOldPass').value = '';
                document.getElementById('profileNewPass').value = '';
                document.getElementById('profileA1').value = '';
                document.getElementById('profileA2').value = '';
                document.getElementById('profileSecurityConfirmPass').value = '';
                fetchCurrentQuestionsForProfile();
            }
        }

        async function fetchCurrentQuestionsForProfile() {
            try {
                const res = await fetch(`/api/fetch-questions?profile_name=${encodeURIComponent(currentUser)}`);
                if(res.ok) {
                    const data = await res.json();
                    document.getElementById('profileQ1').value = data.q1;
                    document.getElementById('profileQ2').value = data.q2;
                }
            } catch(e) {
                console.error("Failed to load historical challenge presets.");
            }
        }

        function toggleRegisterMode(mode) {
            isRegisterMode = mode;
            const container = document.getElementById('securityQuestionsFields');
            const title = document.getElementById('authFormTitle');
            const actions = document.getElementById('authActions');
            const pLabel = document.getElementById('profileLabel');
            const pHint = document.getElementById('profileHint');
            
            if(mode) {
                title.innerHTML = "<h3>Create New Secured Account</h3>";
                pLabel.innerText = "Choose Unique Profile Name:";
                pHint.innerText = "This profile name identifier will be locked to your personal roadmap history data logs.";
                container.style.display = 'block';
                actions.innerHTML = `
                    <button class="submit-btn" style="background:#2e7d32;" onclick="handleAuth('/api/signup')">Register & Save Account</button>
                    <button class="secondary-link" onclick="toggleRegisterMode(false)">Already have an account? Login</button>
                `;
            } else {
                title.innerHTML = "<h3>Sign In / Register</h3>";
                pLabel.innerText = "Account Profile Name:";
                pHint.innerText = "Must be a single, continuous word with no spaces or special symbols.";
                container.style.display = 'none';
                actions.innerHTML = `
                    <button class="submit-btn" onclick="handleAuth('/api/login')">Login</button>
                    <button class="secondary-link" onclick="toggleRegisterMode(true)">New here? Create Account with Security Questions</button>
                    <button class="secondary-link" onclick="switchToForgotView()">Forgot Password?</button>
                `;
            }
        }

        function switchToForgotView() {
            document.getElementById('authView').style.display = 'none';
            document.getElementById('forgotView').style.display = 'block';
            document.getElementById('challengeContainer').style.display = 'none';
        }

        function switchToLoginView() {
            document.getElementById('forgotView').style.display = 'none';
            document.getElementById('authView').style.display = 'block';
            toggleRegisterMode(false);
        }

        async function fetchUserQuestions() {
            const profileName = document.getElementById('forgotProfileName').value.trim();
            if(!profileName) return alert("Please type your profile name first.");
            
            try {
                const res = await fetch(`/api/fetch-questions?profile_name=${encodeURIComponent(profileName)}`);
                if(!res.ok) {
                    const errorData = await res.json();
                    throw new Error(errorData.detail || "Account missing.");
                }
                const data = await res.json();
                
                document.getElementById('challengePrompt1').innerText = "1. " + data.q1;
                document.getElementById('challengePrompt2').innerText = "2. " + data.q2;
                document.getElementById('challengeContainer').style.display = 'block';
            } catch(e) {
                alert("Recovery Configuration Failure: " + e.message);
            }
        }

        async function verifyRecoveryChallenge() {
            const profileName = document.getElementById('forgotProfileName').value.trim();
            const a1 = document.getElementById('challengeAns1').value;
            const a2 = document.getElementById('challengeAns2').value;

            try {
                const res = await fetch('/api/verify-recovery', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ profile_name: profileName, answer1: a1, answer2: a2 })
                });

                if(!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail);
                }
                const data = await res.json();
                alert(`🎯 Verification Successful! Your matching access password is: ${data.password}`);
                switchToLoginView();
                document.getElementById('authPassword').value = data.password;
                document.getElementById('authProfileName').value = profileName;
            } catch(e) {
                alert("Verification Failed: " + e.message);
            }
        }

        async function handleAuth(endpoint) {
            const profileName = document.getElementById('authProfileName').value.trim();
            const password = document.getElementById('authPassword').value;
            if(!profileName || !password) return alert("Please specify validation parameters.");

            let bodyData = { profile_name: profileName, password: password };
            
            if(isRegisterMode) {
                bodyData.question1 = document.getElementById('regQ1').value;
                bodyData.answer1 = document.getElementById('regA1').value;
                bodyData.question2 = document.getElementById('regQ2').value;
                bodyData.answer2 = document.getElementById('regA2').value;

                if(!bodyData.answer1 || !bodyData.answer2) return alert("Please provide answers to both security challenge questions.");
            }

            try {
                const res = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(bodyData)
                });
                const data = await res.json();

                if(!res.ok) {
                    throw new Error(data.detail || "Authentication fault.");
                }
                
                if(endpoint === '/api/signup') {
                    alert("Account setup complete! Moving to log in workflow.");
                    toggleRegisterMode(false);
                } else {
                    localStorage.setItem('profileName', data.profile_name);
                    currentUser = data.profile_name;
                    checkSession();
                }
            } catch(err) {
                alert("Portal Access Error: " + err.message);
            }
        }

        async function updateSecurityQuestions() {
            const q1 = document.getElementById('profileQ1').value;
            const a1 = document.getElementById('profileA1').value.trim();
            const q2 = document.getElementById('profileQ2').value;
            const a2 = document.getElementById('profileA2').value.trim();
            const confirmPass = document.getElementById('profileSecurityConfirmPass').value;

            if(!a1 || !a2 || !confirmPass) {
                return alert("Fulfill both configuration challenge answers and your valid password to proceed.");
            }

            try {
                const res = await fetch('/api/update-security-questions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        profile_name: currentUser,
                        password_validation: confirmPass,
                        question1: q1,
                        answer1: a1,
                        question2: q2,
                        answer2: a2
                    })
                });

                const data = await res.json();
                if(!res.ok) throw new Error(data.detail || "Server logic validation fault.");

                alert("🎯 Security challenge loops updated! Verification credentials refreshed.");
                document.getElementById('profileA1').value = '';
                document.getElementById('profileA2').value = '';
                document.getElementById('profileSecurityConfirmPass').value = '';
            } catch(e) {
                alert("Update Rejected: " + e.message);
            }
        }

        async function updateUserPassword() {
            const oldPass = document.getElementById('profileOldPass').value;
            const newPass = document.getElementById('profileNewPass').value;

            if(!oldPass || !newPass) {
                return alert("Please fulfill both password values to perform this configuration change.");
            }
            if(newPass.length < 6) {
                return alert("The target password sequence must be at least 6 characters long.");
            }

            try {
                const res = await fetch('/api/update-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        profile_name: currentUser,
                        old_password: oldPass,
                        new_password: newPass
                    })
                });

                const data = await res.json();
                if(!res.ok) throw new Error(data.detail || "Execution runtime exception.");

                alert("🎯 Password modification succeeded! Security state synchronized successfully.");
                document.getElementById('profileOldPass').value = '';
                document.getElementById('profileNewPass').value = '';
            } catch(e) {
                alert("Security Action Cancelled: " + e.message);
            }
        }

        async function runAnalysis() {
            const target = document.getElementById('targetJob').value;
            if(!target) return alert("Please specify a profession profile target.");
            
            const btn = document.getElementById('analyzeBtn');
            btn.disabled = true;
            btn.innerText = "Generating Global Roadmap (Streaming AI Analysis)...";

            const formData = new FormData();
            formData.append("profile_name", currentUser);
            formData.append("target_job", target);
            
            const fileInput = document.getElementById('cvFile');
            if(fileInput.files.length > 0) formData.append("file", fileInput.files[0]);

            try {
                const res = await fetch('/api/analyze', { method: 'POST', body: formData });
                if (!res.ok) {
                    const errorData = await res.json();
                    throw new Error(errorData.detail || "Server Error");
                }
                const data = await res.json();
                
                renderDashboard(data);
                renderInterviewPrep(data.interview_prep);
            } catch (err) {
                alert("Advisor Validation Alert: " + err.message);
            } finally {
                btn.disabled = false;
                btn.innerText = "Analyze & Generate Roadmap";
            }
        }

        function renderDashboard(data) {
            document.getElementById('resultDashboard').style.display = 'block';
            document.getElementById('targetJob').value = data.target_job;
            document.getElementById('realityCheck').innerText = "Industry Reality Check — " + data.reality_check;
            
            document.getElementById('statSubjects').innerText = data.core_subjects.length;
            document.getElementById('statStages').innerText = data.pathway.length;
            document.getElementById('statYears').innerText = data.timeline_duration;

            renderBadges('groupCore', data.core_subjects, 'core');
            renderBadges('groupSupport', data.supporting_skills, 'support');
            renderBadges('groupExtra', data.standout_extras, 'extra');

            const timeline = document.getElementById('pathwayTimeline');
            timeline.innerHTML = '';
            data.pathway.forEach((step, idx) => {
                timeline.innerHTML += `
                    <div class="timeline-item">
                        <div class="timeline-num">${idx + 1}</div>
                        <strong style="color:var(--text-strong);">${step.title}</strong><br>
                        <span style="font-size:14px; opacity:0.8;">${step.details}</span><br>
                        <small style="color:var(--primary); font-weight:bold;">${step.duration}</small>
                    </div>`;
            });
        }

        function renderBadges(containerId, list, typeClass) {
            const el = document.getElementById(containerId);
            el.innerHTML = '';
            list.forEach(item => { el.innerHTML += `<span class="badge ${typeClass}">${item}</span>`; });
        }

        function renderInterviewPrep(questions) {
            const container = document.getElementById('interviewContainer');
            container.innerHTML = '<h3 style="margin-bottom:20px; color:var(--text-strong);">Tailored Industry Drill Questions</h3>';
            questions.forEach((q, idx) => {
                container.innerHTML += `
                    <div style="background:var(--bg-card); padding:20px; border-radius:8px; margin-bottom:15px; border: 1px solid var(--border); border-left:4px solid var(--primary);">
                        <div style="font-weight:bold; color:var(--text-strong); margin-bottom: 6px;">Q${idx+1}: ${q.question}</div>
                        <div style="font-size:14px; color:var(--text-muted); font-style:italic;">💡 Strategy: ${q.optimal_response_strategy}</div>
                    </div>`;
            });
        }

        async function loadHistoryLogs() {
            try {
                const res = await fetch(`/api/history?profile_name=${encodeURIComponent(currentUser)}`);
                const logs = await res.json();
                const body = document.getElementById('historyTableBody');
                body.innerHTML = '';
                
                if (logs.length === 0) {
                    body.innerHTML = '<tr><td colspan="3" style="text-align:center; color:var(--text-muted);">No saved historical analyses profiles found for your account.</td></tr>';
                    return;
                }

                logs.forEach(log => {
                    body.innerHTML += `
                        <tr class="clickable-row" onclick="restoreHistoricalRoadmap(${log.id})">
                            <td>${log.date}</td>
                            <td style="font-weight:bold; color:var(--text-strong);">${log.target_job}</td>
                            <td style="text-align:center;" onclick="event.stopPropagation();">
                                <button class="delete-btn" onclick="deleteHistoryLog(${log.id})" title="Delete entry permanently">🗑️</button>
                            </td>
                        </tr>
                    `;
                });
            } catch (err) {
                console.error("Failed loading history logs.");
            }
        }

        async function restoreHistoricalRoadmap(profileId) {
            try {
                const res = await fetch(`/api/history/${profileId}`);
                if (!res.ok) return alert("Record missing.");
                const historicalData = await res.json();
                
                renderDashboard(historicalData);
                renderInterviewPrep(historicalData.interview_prep);
                setView('analyze');
            } catch (e) {
                alert("Connection failed.");
            }
        }

        async function deleteHistoryLog(profileId) {
            if (!confirm("Are you sure you want to permanently delete this career roadmap from your log?")) return;
            
            try {
                const res = await fetch(`/api/history/${profileId}`, { method: 'DELETE' });
                if (res.ok) {
                    loadHistoryLogs();
                } else {
                    alert("Could not remove log instance from server storage.");
                }
            } catch (err) {
                alert("Communication failure processing record deletion layout loops.");
            }
        }

        function toggleTheme() {
            const root = document.documentElement;
            const btn = document.getElementById('themeBtn');
            if (root.getAttribute('data-theme') === 'dark') {
                root.setAttribute('data-theme', 'light');
                btn.innerText = "🌙 Dark Mode";
            } else {
                root.setAttribute('data-theme', 'dark');
                btn.innerText = "☀️ Bright Mode";
            }
        }

        function togglePasswordVisibility(fieldId, buttonId) {
            const passField = document.getElementById(fieldId);
            const eyeBtn = document.getElementById(buttonId);
            passField.type = passField.type === "password" ? "text" : "password";
            eyeBtn.innerText = passField.type === "password" ? "👁️ Show" : "🔒 Hide";
        }

        function checkSession() {
            if(currentUser) {
                document.getElementById('authView').style.display = 'none';
                document.getElementById('forgotView').style.display = 'none';
                document.getElementById('userProfileArea').style.display = 'block';
                document.getElementById('profileDisplayTag').innerText = currentUser;
                setView('analyze');
            } else {
                document.getElementById('authView').style.display = 'block';
                document.getElementById('forgotView').style.display = 'none';
                document.getElementById('userProfileArea').style.display = 'none';
                
                document.getElementById('analyzeView').style.display = 'none';
                document.getElementById('interviewView').style.display = 'none';
                document.getElementById('historyView').style.display = 'none';
                document.getElementById('profileView').style.display = 'none';
                document.getElementById('aboutView').style.display = 'none';
                
                document.getElementById('resultDashboard').style.display = 'none';
                document.getElementById('interviewContainer').innerHTML = '<p style="color:var(--text-muted);">Run an advisor roadmap analysis first to fill this dashboard view.</p>';
                toggleRegisterMode(false);
            }
        }

        function logout() {
            localStorage.removeItem('profileName');
            currentUser = "";
            checkSession();
        }

        window.onload = checkSession;
    </script>
</body>
</html>
"""

# --- BACKEND REST API ---

@app.get("/", response_class=HTMLResponse)
async def get_index():
    return HTML_CONTENT

@app.post("/api/signup")
async def signup(user: UserAuth):
    normalized_name = user.profile_name.strip().lower()
    if not normalized_name:
        raise HTTPException(status_code=400, detail="Profile Name cannot be empty values.")
        
    if normalized_name in USER_DB:
        raise HTTPException(status_code=400, detail="An account with this profile name already exists.")
    
    if len(user.password) < 6:
        raise HTTPException(status_code=400, detail="Password credentials must be at least 6 characters long.")
        
    if not user.question1 or not user.answer1 or not user.question2 or not user.answer2:
        raise HTTPException(status_code=400, detail="Registration requires 2 valid security challenge answers.")
    
    USER_DB[normalized_name] = {
        "password": user.password,
        "q1": user.question1,
        "a1": user.answer1.strip().lower(),
        "q2": user.question2,
        "a2": user.answer2.strip().lower()
    }
    return {"status": "success"}

@app.post("/api/login")
async def login(user: UserAuth):
    normalized_name = user.profile_name.strip().lower()
    
    if normalized_name not in USER_DB:
        raise HTTPException(
            status_code=401, 
            detail="Authentication Error: This profile name does not exist. Please register first."
        )
        
    if USER_DB[normalized_name]["password"] != user.password:
        raise HTTPException(status_code=401, detail="Invalid account password credentials.")
        
    return {"status": "success", "profile_name": normalized_name}

@app.post("/api/update-password")
async def update_password(payload: PasswordUpdate):
    normalized_name = payload.profile_name.strip().lower()
    
    if normalized_name not in USER_DB:
        raise HTTPException(status_code=404, detail="Target account profile configuration missing.")
        
    if USER_DB[normalized_name]["password"] != payload.old_password:
        raise HTTPException(status_code=401, detail="Current verification password configuration is inaccurate.")
        
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="Target password value must be at least 6 characters in length.")
        
    USER_DB[normalized_name]["password"] = payload.new_password
    return {"status": "success", "detail": "Account credential sequence adjusted successfully."}

# NEW ENDPOINT: SECURITY QUESTIONS MANAGEMENT LOOPS
@app.post("/api/update-security-questions")
async def update_security_questions(payload: SecurityQuestionsUpdate):
    normalized_name = payload.profile_name.strip().lower()
    
    if normalized_name not in USER_DB:
        raise HTTPException(status_code=404, detail="Profile record target instance absent.")
        
    if USER_DB[normalized_name]["password"] != payload.password_validation:
        raise HTTPException(status_code=401, detail="Authentication Failure: Action requires valid profile password.")
        
    if not payload.answer1.strip() or not payload.answer2.strip():
        raise HTTPException(status_code=400, detail="Security options require non-empty validation parameters.")

    USER_DB[normalized_name]["q1"] = payload.question1
    USER_DB[normalized_name]["a1"] = payload.answer1.strip().lower()
    USER_DB[normalized_name]["q2"] = payload.question2
    USER_DB[normalized_name]["a2"] = payload.answer2.strip().lower()
    
    return {"status": "success", "detail": "Security verification presets modified safely."}

@app.get("/api/fetch-questions")
async def fetch_questions(profile_name: str):
    normalized_name = profile_name.strip().lower()
    if normalized_name not in USER_DB:
        raise HTTPException(status_code=404, detail="No registered configuration matched this profile name.")
    return {
        "q1": USER_DB[normalized_name]["q1"],
        "q2": USER_DB[normalized_name]["q2"]
    }

@app.post("/api/verify-recovery")
async def verify_recovery(challenge: PasswordRecoveryVerify):
    normalized_name = challenge.profile_name.strip().lower()
    if normalized_name not in USER_DB:
        raise HTTPException(status_code=404, detail="Profile name not found.")
        
    user_record = USER_DB[normalized_name]
    provided_a1 = challenge.answer1.strip().lower()
    provided_a2 = challenge.answer2.strip().lower()
    
    if user_record["a1"] == provided_a1 and user_record["a2"] == provided_a2:
        return {"status": "success", "password": user_record["password"]}
        
    raise HTTPException(status_code=400, detail="Security challenge responses did not match profile parameters.")


@app.get("/api/history")
async def get_user_history(profile_name: str = "guest"):
    user_filtered_list = [item for item in HISTORY_DB if item.get("profile_name") == profile_name.strip().lower()]
    return user_filtered_list

@app.get("/api/history/{profile_id}")
async def get_single_history(profile_id: int):
    for item in HISTORY_DB:
        if item["id"] == profile_id:
            return item
    raise HTTPException(status_code=404, detail="Not Found")

@app.delete("/api/history/{profile_id}")
async def delete_single_history(profile_id: int):
    global HISTORY_DB
    for index, item in enumerate(HISTORY_DB):
        if item["id"] == profile_id:
            HISTORY_DB.pop(index)
            return {"status": "success", "detail": f"Record {profile_id} removed completely"}
    raise HTTPException(status_code=404, detail="Record not found in system state memory cache.")

@app.post("/api/analyze")
async def analyze(
    profile_name: str = Form("guest"),
    target_job: str = Form(...),
    file: UploadFile = File(None)
):
    normalized_job = target_job.strip().lower()
    forbidden_keywords = [
        "goon", "thief", "robber", "gangster", "mobster", "hitman", "assassin",
        "pornstar", "porn", "adult actor", "escort", "prostitute", "pimp",
        "drug dealer", "smuggler", "hacker", "scammer","adult film actress","adult film actor","adult film performer"
    ]
    if any(keyword in normalized_job for keyword in forbidden_keywords):
        raise HTTPException(
            status_code=400, 
            detail="Safety Refusal: CareerLens cannot generate career roadmaps or preparation modules for illegal, harmful, or illicit occupations."
        )

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    new_id = int(datetime.datetime.now().timestamp())

    prompt_text = f"""
    You are an elite, highly expert global career counselor intelligence platform.
    The user has requested a completely customized preparation blueprint and structural training sequence to transition into this specific profession: "{target_job}".
    
    Provide an accurate industry roadmap, broken down structurally into milestone sequences, explicit core subjects, competency categories, and a targeted list of evaluation/audition/interview questions.
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_text,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=UniversalRoadmapResponse,
                temperature=0.2
            ),
        )

        import json
        structured_data = json.loads(response.text)
        
        structured_data["id"] = new_id
        structured_data["date"] = timestamp
        structured_data["profile_name"] = profile_name.strip().lower()  
        
        HISTORY_DB.append(structured_data)
        return structured_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Live AI Engine compilation failure: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    import socket

    def find_free_port(start_port: int) -> int:
        port = start_port
        while port < 65535:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                if sock.connect_ex(('127.0.0.1', port)) != 0:
                    return port
            port += 1
        return start_port

    free_port = find_free_port(8000)
    print(f"\\n🚀 CareerLens Live Model Adapter Engine Routing to: http://127.0.0.1:{free_port}\\n")
    uvicorn.run(app, host="127.0.0.1", port=free_port)
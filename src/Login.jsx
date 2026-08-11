import React, { useState } from 'react';
import { Eye, EyeOff, Loader2 } from 'lucide-react';
import './Login.css';

export default function Login() {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    rememberMe: false,
  });

  const [errors, setErrors] = useState({
    email: '',
    password: '',
  });

  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [loginSuccess, setLoginSuccess] = useState(false);

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));

    if (errors[name]) {
      setErrors((prev) => ({
        ...prev,
        [name]: '',
      }));
    }
  };

  const validateForm = () => {
    let isValid = true;
    const newErrors = { email: '', password: '' };

    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
      isValid = false;
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email address';
      isValid = false;
    }

    if (!formData.password) {
      newErrors.password = 'Password is required';
      isValid = false;
    }

    setErrors(newErrors);
    return isValid;
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!validateForm()) return;

    setIsLoading(true);
    setLoginSuccess(false);

    // Simulate API request
    setTimeout(() => {
      setIsLoading(false);
      setLoginSuccess(true);
      
      // Auto reset success message after 3 seconds
      setTimeout(() => {
        setLoginSuccess(false);
      }, 3000);
    }, 1500);
  };

  return (
    <div className="login-page-wrapper">
      {/* Background abstract medical/blood flow shapes */}
      <div className="flow-shape shape-glow-top-left"></div>
      <div className="flow-shape shape-glow-bottom-right"></div>
      <div className="flow-shape shape-circle-light-1"></div>
      <div className="flow-shape shape-circle-light-2"></div>

      {/* Layered fluid blood flow wave paths */}
      <div className="blood-flow-waves">
        <svg viewBox="0 0 1440 900" fill="none" xmlns="http://www.w3.org/2000/svg" className="flow-wave-svg">
          {/* Wave 1: Burgundy/Rose flow */}
          <path d="M-100 450 C250 600, 600 300, 1000 500 C1200 580, 1400 450, 1600 480" stroke="url(#flow-grad-1)" strokeWidth="3.5" strokeOpacity="0.08" strokeLinecap="round" />
          {/* Wave 2: Crimson/Pink flow */}
          <path d="M-50 400 C300 520, 700 250, 1100 420 C1300 500, 1450 380, 1650 410" stroke="url(#flow-grad-2)" strokeWidth="2.5" strokeOpacity="0.06" strokeLinecap="round" />
          {/* Wave 3: Muted pink flow */}
          <path d="M-80 350 C280 470, 650 200, 1050 380 C1250 450, 1380 330, 1580 360" stroke="url(#flow-grad-3)" strokeWidth="2" strokeOpacity="0.04" strokeLinecap="round" />
          
          <defs>
            <linearGradient id="flow-grad-1" x1="0" y1="0" x2="1440" y2="900" gradientUnits="userSpaceOnUse">
              <stop stopColor="#881337" />
              <stop offset="0.5" stopColor="#E51B3E" />
              <stop offset="1" stopColor="#FDA4AF" />
            </linearGradient>
            <linearGradient id="flow-grad-2" x1="0" y1="0" x2="1440" y2="900" gradientUnits="userSpaceOnUse">
              <stop stopColor="#E51B3E" />
              <stop offset="0.7" stopColor="#FDA4AF" />
              <stop offset="1" stopColor="#FFF1F2" />
            </linearGradient>
            <linearGradient id="flow-grad-3" x1="0" y1="0" x2="1440" y2="900" gradientUnits="userSpaceOnUse">
              <stop stopColor="#BE123C" />
              <stop offset="1" stopColor="#E2E8F0" />
            </linearGradient>
          </defs>
        </svg>
      </div>

      <div className="login-card">
        <div className="brand-header">
          <div className="brand-logo">
            {/* Unified start-up style gradient blood drop logo */}
            <svg width="24" height="28" viewBox="0 0 28 32" fill="none" xmlns="http://www.w3.org/2000/svg" className="logo-svg">
              <defs>
                <linearGradient id="logo-drop-grad" x1="14" y1="1" x2="14" y2="31" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stopColor="#FF3358" />
                  <stop offset="100%" stopColor="#C41230" />
                </linearGradient>
              </defs>
              <path d="M14 1C14 1 2 13 2 21C2 27.075 7.373 31 14 31C20.627 31 26 27.075 26 21C26 13 14 1 14 1Z" fill="url(#logo-drop-grad)" />
              <path d="M8 18C8 14 11 10 13.5 8" stroke="white" strokeWidth="2" strokeLinecap="round" opacity="0.35" />
            </svg>
          </div>
          <span className="brand-name">Rakthasedu</span>
        </div>

        <div className="login-heading">
          <h2>Welcome Back</h2>
          <p>Sign in to continue</p>
        </div>

        {loginSuccess && (
          <div className="success-banner">
            <span>Signed in successfully!</span>
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          {/* Email Field */}
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleInputChange}
              placeholder="Enter your email"
              disabled={isLoading}
              className={errors.email ? 'input-error' : ''}
            />
            {errors.email && (
              <span className="error-message">{errors.email}</span>
            )}
          </div>

          {/* Password Field */}
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <div className="password-input-container">
              <input
                type={showPassword ? 'text' : 'password'}
                id="password"
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                placeholder="Enter your password"
                disabled={isLoading}
                className={errors.password ? 'input-error' : ''}
              />
              <button
                type="button"
                className="password-toggle-btn"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                disabled={isLoading}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {errors.password && (
              <span className="error-message">{errors.password}</span>
            )}
          </div>

          {/* Remember Me & Forgot Password Row */}
          <div className="form-row">
            <label className="checkbox-label-container">
              <input
                type="checkbox"
                name="rememberMe"
                checked={formData.rememberMe}
                onChange={handleInputChange}
                disabled={isLoading}
              />
              <span className="checkbox-text">Remember me</span>
            </label>
            <a href="#forgot" className="forgot-link" onClick={(e) => e.preventDefault()}>
              Forgot password?
            </a>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            className="submit-btn"
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="spinner" size={16} />
                <span>Signing In...</span>
              </>
            ) : (
              'Sign In'
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

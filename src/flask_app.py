"""Flask application that wraps FastAPI routes with a UI."""
from __future__ import annotations

import os

import requests
from flask import Flask, jsonify, redirect, render_template_string, request, url_for

app = Flask(__name__)

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}AIP-C01 Prep{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'media',
            theme: {
                extend: {
                    colors: {
                        primary: {"50":"#eef2ff","100":"#e0e7ff","200":"#c7d2fe","300":"#a5b4fc","400":"#818cf8","500":"#6366f1","600":"#4f46e5","700":"#4338ca","800":"#3730a3","900":"#312e81"}
                    }
                }
            }
        }
    </script>
    <style type="text/tailwindcss">
        @layer components {
            .btn-primary {
                @apply bg-primary-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-primary-700 transition-all duration-200 shadow-sm hover:shadow-md;
            }
            .btn-success {
                @apply bg-emerald-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-emerald-700 transition-all duration-200 shadow-sm hover:shadow-md;
            }
            .btn-danger {
                @apply bg-red-500 text-white px-3 py-1.5 rounded-md text-sm font-medium hover:bg-red-600 transition-all duration-200;
            }
            .card {
                @apply bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 dark:border-gray-700 overflow-hidden;
            }
            .card-header {
                @apply px-6 py-4 border-b border-gray-100 dark:border-gray-700 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 dark:bg-gray-800/50;
            }
            .card-body {
                @apply p-6;
            }
            .form-group {
                @apply space-y-1.5;
            }
            .form-label {
                @apply block text-sm font-medium text-gray-700 dark:text-gray-300 dark:text-gray-300;
            }
            .form-input {
                @apply w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-sm text-gray-900 dark:text-gray-100 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all duration-200 bg-white dark:bg-gray-700;
            }
            .form-textarea {
                @apply w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-sm text-gray-900 dark:text-gray-100 dark:text-gray-100 font-mono focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all duration-200 bg-white dark:bg-gray-700 resize-none;
            }
            .form-select {
                @apply w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-sm text-gray-900 dark:text-gray-100 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all duration-200 bg-white dark:bg-gray-700;
            }
            .form-checkbox {
                @apply w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500 transition-all duration-200;
            }
            .section-card {
                @apply bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 dark:border-gray-700 overflow-hidden;
            }
            .section-header {
                @apply px-5 py-3 bg-gradient-to-r from-gray-50 to-white dark:from-gray-800 dark:to-gray-800 border-b border-gray-200 dark:border-gray-700 dark:border-gray-700 flex items-center gap-2;
            }
            .section-title {
                @apply text-base font-semibold text-gray-800 dark:text-gray-200 dark:text-gray-200;
            }
            .section-body {
                @apply p-5;
            }
            .badge {
                @apply px-2.5 py-1 text-xs font-medium rounded-full;
            }
            .badge-blue {
                @apply bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300;
            }
            .badge-green {
                @apply bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300;
            }
            .badge-red {
                @apply bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300;
            }
            .badge-gray {
                @apply bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 dark:text-gray-300;
            }
            .badge-amber {
                @apply bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300;
            }
            .badge-purple {
                @apply bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300;
            }
            .metric-card {
                @apply bg-gradient-to-br from-gray-50 to-white dark:from-gray-800 dark:to-gray-800 p-4 rounded-xl border border-gray-100 dark:border-gray-700 dark:border-gray-700;
            }
            .metric-value {
                @apply text-2xl font-bold text-primary-600 dark:text-primary-400;
            }
            .metric-label {
                @apply text-xs font-medium text-gray-500 dark:text-gray-400 dark:text-gray-400 uppercase tracking-wide;
            }
            .tooltip-trigger {
                @apply inline-flex items-center justify-center w-4 h-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help transition-colors;
            }
            .tooltip-content {
                @apply invisible opacity-0 absolute z-50 px-3 py-2 text-xs font-normal text-white bg-gray-900 dark:bg-gray-700 rounded-lg shadow-lg whitespace-normal max-w-xs left-1/2 -translate-x-1/2 bottom-full mb-2 transition-all duration-200;
            }
            .tooltip-content::after {
                content: '';
                @apply absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900 dark:border-t-gray-700;
            }
            .group:hover .tooltip-content {
                @apply visible opacity-100;
            }
        }
    </style>
</head>
<body class="bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-950 min-h-screen text-gray-900 dark:text-gray-100 dark:text-gray-100">
    <nav class="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 dark:border-gray-700 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex items-center justify-between h-16">
                <a href="/" class="flex items-center gap-2">
                    <div class="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center">
                        <span class="text-white font-bold text-sm">AI</span>
                    </div>
                    <span class="text-lg font-semibold text-gray-900 dark:text-gray-100 dark:text-gray-100">AIP-C01 Prep</span>
                </a>
                <div class="flex items-center gap-1">
                    <a href="/" class="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 dark:text-gray-300 hover:text-gray-900 dark:text-gray-100 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-all">Home</a>
                    <a href="/datasets" class="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 dark:text-gray-300 hover:text-gray-900 dark:text-gray-100 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-all">Datasets</a>
                    <a href="/configs" class="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 dark:text-gray-300 hover:text-gray-900 dark:text-gray-100 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-all">Configs</a>
                    <a href="/experiments" class="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 dark:text-gray-300 hover:text-gray-900 dark:text-gray-100 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-all">Experiments</a>
                    <a href="/benchmarks" class="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 dark:text-gray-300 hover:text-gray-900 dark:text-gray-100 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-all">Benchmarks</a>
                    <a href="/evaluations" class="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 dark:text-gray-300 hover:text-gray-900 dark:text-gray-100 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-all">Evaluations</a>
                    <a href="/meta" class="px-4 py-2 text-sm font-medium text-purple-600 dark:text-purple-400 hover:text-purple-900 dark:hover:text-purple-300 hover:bg-purple-50 dark:hover:bg-purple-900/30 rounded-lg transition-all">Meta</a>
                </div>
            </div>
        </div>
    </nav>
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {% block content %}{% endblock %}
    </main>
    <script>
    // Convert UTC timestamps to local timezone
    document.addEventListener('DOMContentLoaded', function() {
        document.querySelectorAll('[data-utc]').forEach(function(el) {
            const utc = el.getAttribute('data-utc');
            if (!utc) return;
            try {
                const date = new Date(utc.includes('T') ? utc : utc.replace(' ', 'T') + 'Z');
                if (isNaN(date.getTime())) return;
                const format = el.getAttribute('data-format') || 'datetime';
                if (format === 'date') {
                    el.textContent = date.toLocaleDateString();
                } else if (format === 'time') {
                    el.textContent = date.toLocaleTimeString();
                } else {
                    el.textContent = date.toLocaleString();
                }
            } catch (e) {}
        });
    });
    </script>
</body>
</html>
"""

HOME_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Home - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="max-w-5xl mx-auto">
            <div class="text-center mb-10">
                <h1 class="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-3">ML Experiment Platform</h1>
                <p class="text-lg text-gray-600 dark:text-gray-400">Fine-tune language models with ease</p>
            </div>
            
            <!-- AutoTune Hero Button -->
            <div class="mb-10">
                <button onclick="openAutoTuneModal()" class="w-full p-6 bg-gradient-to-r from-violet-600 via-purple-600 to-indigo-600 hover:from-violet-500 hover:via-purple-500 hover:to-indigo-500 rounded-2xl shadow-lg hover:shadow-xl transition-all group">
                    <div class="flex items-center justify-center gap-4">
                        <div class="w-14 h-14 bg-white/20 rounded-full flex items-center justify-center group-hover:scale-110 transition-transform">
                            <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                            </svg>
                        </div>
                        <div class="text-left">
                            <h2 class="text-2xl font-bold text-white">AutoTune Fine-Tuning</h2>
                            <p class="text-white/80 text-sm">Automatically find the best config, train, and evaluate with one click</p>
                        </div>
                        <svg class="w-6 h-6 text-white/80 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                        </svg>
                    </div>
                </button>
            </div>
            
            <!-- AutoTune Modal -->
            <div id="autotune-modal" class="fixed inset-0 bg-gray-900/60 dark:bg-gray-900/80 backdrop-blur-sm hidden items-center justify-center z-50">
                <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto border border-gray-200 dark:border-gray-700">
                    <div class="p-6 border-b border-gray-200 dark:border-gray-700 sticky top-0 bg-white dark:bg-gray-800">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 bg-gradient-to-br from-violet-500 to-indigo-600 rounded-xl flex items-center justify-center">
                                    <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                                    </svg>
                                </div>
                                <div>
                                    <h3 class="text-xl font-bold text-gray-900 dark:text-gray-100">AutoTune Configuration</h3>
                                    <p class="text-sm text-gray-500 dark:text-gray-400">Configure and launch automated fine-tuning</p>
                                </div>
                            </div>
                            <button onclick="closeAutoTuneModal()" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                            </button>
                        </div>
                    </div>
                    
                    <form id="autotune-form" class="p-6 space-y-6">
                        <!-- Dataset Selection -->
                        <div class="section-card">
                            <div class="section-header">
                                <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"></path></svg>
                                <h4 class="section-title">Dataset</h4>
                            </div>
                            <div class="section-body">
                                <select id="ap-dataset" name="dataset_id" required class="form-select">
                                    <option value="">Select a dataset...</option>
                                    {% for ds in datasets %}
                                    <option value="{{ ds.id }}" data-columns="{{ ds.columns | join(',') }}">{{ ds.filename }} ({{ ds.row_count }} rows)</option>
                                    {% endfor %}
                                </select>
                                <div class="grid grid-cols-2 gap-4 mt-4">
                                    <div class="form-group">
                                        <label class="form-label">Question Field</label>
                                        <input type="text" id="ap-question-field" name="question_field" value="question" class="form-input">
                                    </div>
                                    <div class="form-group">
                                        <label class="form-label">Answer Field</label>
                                        <input type="text" id="ap-answer-field" name="answer_field" value="answer" class="form-input">
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Benchmark Selection -->
                        <div class="section-card">
                            <div class="section-header">
                                <svg class="w-5 h-5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
                                <h4 class="section-title">Benchmark</h4>
                            </div>
                            <div class="section-body">
                                <div class="mb-4">
                                    <label class="form-label">Benchmark Source</label>
                                    <div class="flex gap-4 mt-2">
                                        <label class="flex items-center gap-2 cursor-pointer">
                                            <input type="radio" name="benchmark_source" value="existing" class="text-primary-600" onchange="toggleBenchmarkSource('existing')">
                                            <span class="text-sm text-gray-700 dark:text-gray-300">Use Existing</span>
                                        </label>
                                        <label class="flex items-center gap-2 cursor-pointer">
                                            <input type="radio" name="benchmark_source" value="dataset" class="text-primary-600" onchange="toggleBenchmarkSource('dataset')" checked>
                                            <span class="text-sm text-gray-700 dark:text-gray-300">From Dataset Row</span>
                                        </label>
                                        <label class="flex items-center gap-2 cursor-pointer">
                                            <input type="radio" name="benchmark_source" value="manual" class="text-primary-600" onchange="toggleBenchmarkSource('manual')">
                                            <span class="text-sm text-gray-700 dark:text-gray-300">Enter Manually</span>
                                        </label>
                                    </div>
                                </div>
                                
                                <!-- Existing Benchmark -->
                                <div id="benchmark-existing" class="hidden">
                                    <select id="ap-benchmark" name="benchmark_id" class="form-select">
                                        <option value="">Select a benchmark...</option>
                                        {% for bm in benchmarks %}
                                        <option value="{{ bm.id }}">{{ bm.name }}: {{ bm.question | truncate(50) }}</option>
                                        {% endfor %}
                                    </select>
                                </div>
                                
                                <!-- From Dataset Row -->
                                <div id="benchmark-dataset">
                                    <div class="form-group">
                                        <label class="form-label">Row Index (0-based)</label>
                                        <input type="number" id="ap-row-idx" name="benchmark_row_idx" value="0" min="0" class="form-input" onchange="loadRowPreview()">
                                        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Uses this row's question/answer as the benchmark</p>
                                    </div>
                                    <div id="row-preview" class="mt-4 hidden">
                                        <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 space-y-3">
                                            <div>
                                                <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">Question</p>
                                                <p id="row-preview-question" class="text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 p-2 rounded border border-gray-200 dark:border-gray-600"></p>
                                            </div>
                                            <div>
                                                <p class="text-xs font-medium text-emerald-600 uppercase mb-1">Answer</p>
                                                <p id="row-preview-answer" class="text-sm text-gray-900 dark:text-gray-100 bg-emerald-50 dark:bg-emerald-900/30 p-2 rounded border border-emerald-200 dark:border-emerald-700"></p>
                                            </div>
                                        </div>
                                    </div>
                                    <p id="row-preview-error" class="mt-2 text-xs text-red-500 hidden"></p>
                                </div>
                                
                                <!-- Manual Entry -->
                                <div id="benchmark-manual" class="hidden space-y-4">
                                    <div class="form-group">
                                        <label class="form-label">Question</label>
                                        <textarea id="ap-question" name="benchmark_question" rows="2" class="form-textarea" placeholder="Enter the benchmark question..."></textarea>
                                    </div>
                                    <div class="form-group">
                                        <label class="form-label">Expected Answer</label>
                                        <textarea id="ap-answer" name="benchmark_answer" rows="2" class="form-textarea" placeholder="Enter the expected answer..."></textarea>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Base Config Selection -->
                        <div class="section-card">
                            <div class="section-header">
                                <svg class="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                                <h4 class="section-title">Base Config</h4>
                            </div>
                            <div class="section-body">
                                <select id="ap-config" name="base_config_id" class="form-select">
                                    <option value="">Use Sensible Defaults (TinyLlama + LoRA)</option>
                                    {% for cfg in configs %}
                                    {% if cfg.experiment_type == 'causal_lm' %}
                                    <option value="{{ cfg.id }}">{{ cfg.name }} ({{ cfg.config.model.pretrained_model_name | truncate(30) }})</option>
                                    {% endif %}
                                    {% endfor %}
                                </select>
                                <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">The optimizer will vary learning rate, LoRA rank, batch size, and epochs around this base config</p>
                            </div>
                        </div>
                        
                        <!-- Training Options -->
                        <div class="section-card">
                            <div class="section-header">
                                <svg class="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"></path></svg>
                                <h4 class="section-title">Training Options</h4>
                            </div>
                            <div class="section-body">
                                <div class="grid grid-cols-2 gap-4">
                                    <div class="form-group">
                                        <label class="form-label">Configs to Train</label>
                                        <select id="ap-top-k" name="top_k" class="form-select">
                                            <option value="3">Top 3 configs</option>
                                            <option value="5" selected>Top 5 configs</option>
                                            <option value="7">Top 7 configs</option>
                                        </select>
                                    </div>
                                    <div class="form-group">
                                        <label class="form-label">Probe Steps</label>
                                        <input type="number" id="ap-probe-steps" name="probe_steps" value="5" min="1" max="50" class="form-input">
                                        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Lower = faster but less accurate predictions</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Submit Button -->
                        <div class="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                            <button type="button" onclick="closeAutoTuneModal()" class="px-4 py-2 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-all">Cancel</button>
                            <button type="submit" id="autotune-submit" class="btn-primary px-8 flex items-center gap-2">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                                Launch AutoTune
                            </button>
                        </div>
                    </form>
                </div>
            </div>
            
            <!-- AutoTune Progress Modal -->
            <div id="autotune-progress" class="fixed inset-0 bg-gray-900/60 dark:bg-gray-900/80 backdrop-blur-sm hidden items-center justify-center z-50">
                <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto border border-gray-200 dark:border-gray-700">
                    <div class="p-6">
                        <div class="text-center mb-6">
                            <div class="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-violet-500 to-indigo-600 rounded-full flex items-center justify-center">
                                <svg id="ap-progress-icon" class="w-8 h-8 text-white animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                                </svg>
                            </div>
                            <h3 id="ap-progress-title" class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2">AutoTune Running</h3>
                            <p id="ap-progress-message" class="text-gray-600 dark:text-gray-400">Starting AutoTune...</p>
                        </div>
                        
                        <!-- Progress Bar -->
                        <div class="mb-6">
                            <div class="flex justify-between text-sm text-gray-500 dark:text-gray-400 mb-2">
                                <span id="ap-phase">Phase: Initializing</span>
                                <span id="ap-status-badge" class="badge badge-blue">pending</span>
                            </div>
                            <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
                                <div id="ap-progress-bar" class="bg-gradient-to-r from-violet-500 to-indigo-600 h-3 rounded-full transition-all duration-500" style="width: 5%"></div>
                            </div>
                        </div>
                        
                        <!-- Candidates Table -->
                        <div id="ap-candidates-section" class="hidden">
                            <h4 class="font-semibold text-gray-800 dark:text-gray-200 mb-3">Config Candidates</h4>
                            <div class="overflow-x-auto">
                                <table class="w-full text-sm">
                                    <thead>
                                        <tr class="bg-gray-50 dark:bg-gray-700">
                                            <th class="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-400">Rank</th>
                                            <th class="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-400">LR</th>
                                            <th class="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-400">LoRA r</th>
                                            <th class="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-400">Batch</th>
                                            <th class="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-400">Epochs</th>
                                            <th class="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-400">Predicted</th>
                                            <th class="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-400">Actual ROUGE</th>
                                        </tr>
                                    </thead>
                                    <tbody id="ap-candidates-body" class="divide-y divide-gray-100 dark:divide-gray-700">
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        
                        <!-- Error Display -->
                        <div id="ap-error-section" class="hidden mt-4 p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg">
                            <p class="text-sm text-red-700 dark:text-red-300" id="ap-error-message"></p>
                        </div>
                        
                        <!-- Action Buttons -->
                        <div class="flex justify-end gap-3 mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
                            <button id="ap-close-progress" onclick="closeProgressModal()" class="hidden px-4 py-2 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-all">Close</button>
                            <a id="ap-view-results" href="#" class="hidden btn-primary px-6">View Results</a>
                        </div>
                    </div>
                </div>
            </div>
            
            <script>
            function openAutoTuneModal() {
                document.getElementById('autotune-modal').classList.remove('hidden');
                document.getElementById('autotune-modal').classList.add('flex');
                loadRowPreview();
            }
            
            function closeAutoTuneModal() {
                document.getElementById('autotune-modal').classList.add('hidden');
                document.getElementById('autotune-modal').classList.remove('flex');
            }
            
            function closeProgressModal() {
                document.getElementById('autotune-progress').classList.add('hidden');
                document.getElementById('autotune-progress').classList.remove('flex');
            }
            
            function toggleBenchmarkSource(source) {
                document.getElementById('benchmark-existing').classList.add('hidden');
                document.getElementById('benchmark-dataset').classList.add('hidden');
                document.getElementById('benchmark-manual').classList.add('hidden');
                document.getElementById('benchmark-' + source).classList.remove('hidden');
                if (source === 'dataset') {
                    loadRowPreview();
                }
            }
            
            async function loadRowPreview() {
                const datasetEl = document.getElementById('ap-dataset');
                const rowIdxEl = document.getElementById('ap-row-idx');
                const questionFieldEl = document.getElementById('ap-question-field');
                const answerFieldEl = document.getElementById('ap-answer-field');
                const previewEl = document.getElementById('row-preview');
                const previewQEl = document.getElementById('row-preview-question');
                const previewAEl = document.getElementById('row-preview-answer');
                const errorEl = document.getElementById('row-preview-error');
                
                const datasetId = datasetEl.value;
                const rowIdx = parseInt(rowIdxEl.value) || 0;
                const questionField = questionFieldEl.value || 'question';
                const answerField = answerFieldEl.value || 'answer';
                
                if (!datasetId) {
                    previewEl.classList.add('hidden');
                    errorEl.classList.add('hidden');
                    return;
                }
                
                try {
                    const resp = await fetch('/api/datasets/' + datasetId + '/row/' + rowIdx);
                    const data = await resp.json();
                    
                    if (!resp.ok) {
                        errorEl.textContent = data.error || 'Failed to load row';
                        errorEl.classList.remove('hidden');
                        previewEl.classList.add('hidden');
                        return;
                    }
                    
                    const question = data.row[questionField] || '(field not found)';
                    const answer = data.row[answerField] || '(field not found)';
                    
                    previewQEl.textContent = question;
                    previewAEl.textContent = answer;
                    previewEl.classList.remove('hidden');
                    errorEl.classList.add('hidden');
                } catch (err) {
                    errorEl.textContent = 'Error loading row preview';
                    errorEl.classList.remove('hidden');
                    previewEl.classList.add('hidden');
                }
            }
            
            // Reload preview when dataset or fields change
            document.getElementById('ap-dataset').addEventListener('change', loadRowPreview);
            document.getElementById('ap-question-field').addEventListener('change', loadRowPreview);
            document.getElementById('ap-answer-field').addEventListener('change', loadRowPreview);
            
            function updateProgress(job) {
                const phaseEl = document.getElementById('ap-phase');
                const msgEl = document.getElementById('ap-progress-message');
                const barEl = document.getElementById('ap-progress-bar');
                const badgeEl = document.getElementById('ap-status-badge');
                const titleEl = document.getElementById('ap-progress-title');
                const candidatesSection = document.getElementById('ap-candidates-section');
                const candidatesBody = document.getElementById('ap-candidates-body');
                const errorSection = document.getElementById('ap-error-section');
                const errorMsg = document.getElementById('ap-error-message');
                const closeBtn = document.getElementById('ap-close-progress');
                const viewBtn = document.getElementById('ap-view-results');
                
                msgEl.textContent = job.phase_message || job.status;
                
                // Update badge
                badgeEl.className = 'badge';
                if (job.status === 'completed') {
                    badgeEl.classList.add('badge-green');
                    badgeEl.textContent = 'completed';
                } else if (job.status === 'failed') {
                    badgeEl.classList.add('badge-red');
                    badgeEl.textContent = 'failed';
                } else if (job.status === 'probing') {
                    badgeEl.classList.add('badge-purple');
                    badgeEl.textContent = 'probing';
                } else if (job.status === 'training') {
                    badgeEl.classList.add('badge-blue');
                    badgeEl.textContent = 'training';
                } else if (job.status === 'evaluating') {
                    badgeEl.classList.add('badge-amber');
                    badgeEl.textContent = 'evaluating';
                } else {
                    badgeEl.classList.add('badge-gray');
                    badgeEl.textContent = job.status;
                }
                
                // Calculate progress
                let progress = 5;
                if (job.status === 'probing') {
                    phaseEl.textContent = 'Phase: Probing configs';
                    progress = 15;
                } else if (job.status === 'training') {
                    phaseEl.textContent = 'Phase: Training (' + (job.current_training_idx + 1) + '/' + job.top_k + ')';
                    progress = 20 + (job.current_training_idx / job.top_k) * 50;
                } else if (job.status === 'evaluating') {
                    phaseEl.textContent = 'Phase: Evaluating (' + (job.current_eval_idx + 1) + '/' + job.top_k + ')';
                    progress = 70 + (job.current_eval_idx / job.top_k) * 25;
                } else if (job.status === 'completed') {
                    phaseEl.textContent = 'Phase: Complete!';
                    titleEl.textContent = 'AutoTune Complete!';
                    progress = 100;
                    closeBtn.classList.remove('hidden');
                    viewBtn.classList.remove('hidden');
                    viewBtn.href = '/evaluations';
                } else if (job.status === 'failed') {
                    phaseEl.textContent = 'Phase: Failed';
                    titleEl.textContent = 'AutoTune Failed';
                    closeBtn.classList.remove('hidden');
                }
                barEl.style.width = progress + '%';
                
                // Show candidates
                if (job.candidates && job.candidates.length > 0) {
                    candidatesSection.classList.remove('hidden');
                    candidatesBody.innerHTML = job.candidates.map((c, i) => {
                        const actualBleu = c.actual_bleu !== null ? c.actual_bleu.toFixed(2) : (job.status === 'training' && i <= job.current_training_idx ? '<span class="animate-pulse">...</span>' : '-');
                        const rowClass = c.actual_bleu !== null && i === 0 ? 'bg-emerald-50 dark:bg-emerald-900/20' : '';
                        return '<tr class="' + rowClass + '"><td class="px-3 py-2 font-medium">#' + c.rank + '</td><td class="px-3 py-2">' + c.learning_rate.toExponential(0) + '</td><td class="px-3 py-2">' + c.lora_r + '</td><td class="px-3 py-2">' + c.batch_size + '</td><td class="px-3 py-2">' + c.num_epochs + '</td><td class="px-3 py-2">' + c.predicted_bleu.toFixed(1) + '</td><td class="px-3 py-2 font-semibold">' + actualBleu + '</td></tr>';
                    }).join('');
                }
                
                // Show error
                if (job.error) {
                    errorSection.classList.remove('hidden');
                    errorMsg.textContent = job.error;
                }
            }
            
            document.getElementById('autotune-form').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const formData = new FormData(this);
                const data = {
                    dataset_id: formData.get('dataset_id'),
                    question_field: formData.get('question_field'),
                    answer_field: formData.get('answer_field'),
                    top_k: parseInt(formData.get('top_k')),
                    probe_steps: parseInt(formData.get('probe_steps')),
                };
                
                // Handle base config
                const baseConfig = formData.get('base_config_id');
                if (baseConfig) {
                    data.base_config_id = baseConfig;
                }
                
                // Handle benchmark source
                const benchmarkSource = formData.get('benchmark_source');
                if (benchmarkSource === 'existing') {
                    data.benchmark_id = formData.get('benchmark_id');
                } else if (benchmarkSource === 'dataset') {
                    data.benchmark_row_idx = parseInt(formData.get('benchmark_row_idx'));
                } else if (benchmarkSource === 'manual') {
                    data.benchmark_question = formData.get('benchmark_question');
                    data.benchmark_answer = formData.get('benchmark_answer');
                }
                
                // Close config modal, show progress modal
                closeAutoTuneModal();
                document.getElementById('autotune-progress').classList.remove('hidden');
                document.getElementById('autotune-progress').classList.add('flex');
                
                try {
                    const resp = await fetch('/api/autotune/run', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data),
                    });
                    
                    const result = await resp.json();
                    
                    if (!resp.ok) {
                        throw new Error(result.detail || 'Failed to start AutoTune');
                    }
                    
                    const jobId = result.job_id;
                    
                    // Poll for updates
                    const poll = async () => {
                        const statusResp = await fetch('/api/autotune/' + jobId);
                        const statusData = await statusResp.json();
                        
                        updateProgress(statusData.job);
                        
                        if (statusData.job.status !== 'completed' && statusData.job.status !== 'failed') {
                            setTimeout(poll, 3000);
                        }
                    };
                    poll();
                    
                } catch (err) {
                    document.getElementById('ap-progress-title').textContent = 'AutoTune Failed';
                    document.getElementById('ap-progress-message').textContent = err.message;
                    document.getElementById('ap-error-section').classList.remove('hidden');
                    document.getElementById('ap-error-message').textContent = err.message;
                    document.getElementById('ap-close-progress').classList.remove('hidden');
                }
            });
            </script>
            
            <!-- Workflow Guide -->
            <div class="card mb-10">
                <div class="card-header">
                    <h2 class="font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
                        <svg class="w-5 h-5 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path></svg>
                        Workflow Guide
                    </h2>
                </div>
                <div class="card-body space-y-3">
                    <!-- Step 1: Upload Dataset -->
                    <a href="/datasets" class="flex items-center gap-4 p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 hover:shadow-md hover:border-blue-300 dark:hover:border-blue-600 transition-all group">
                        <div class="w-10 h-10 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0 group-hover:scale-110 transition-transform">1</div>
                        <div class="flex-grow">
                            <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">Upload Dataset</h3>
                            <p class="text-xs text-gray-600 dark:text-gray-400">Upload CSV with question/answer pairs for training</p>
                        </div>
                        <span class="badge badge-blue">{{ stats.datasets }} datasets</span>
                    </a>
                    
                    <!-- Step 2: Create Config -->
                    <a href="/configs/new" class="flex items-center gap-4 p-4 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-100 dark:border-purple-800 hover:shadow-md hover:border-purple-300 dark:hover:border-purple-600 transition-all group">
                        <div class="w-10 h-10 bg-purple-500 text-white rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0 group-hover:scale-110 transition-transform">2</div>
                        <div class="flex-grow">
                            <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">Create Config</h3>
                            <p class="text-xs text-gray-600 dark:text-gray-400">Define model, training params, and LoRA settings</p>
                        </div>
                    </a>
                    
                    <!-- Step 3: Run Experiment -->
                    <a href="/experiments" class="flex items-center gap-4 p-4 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-100 dark:border-emerald-800 hover:shadow-md hover:border-emerald-300 dark:hover:border-emerald-600 transition-all group">
                        <div class="w-10 h-10 bg-emerald-500 text-white rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0 group-hover:scale-110 transition-transform">3</div>
                        <div class="flex-grow">
                            <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">Run Experiment</h3>
                            <p class="text-xs text-gray-600 dark:text-gray-400">Train Masked LM or Causal LM with your config</p>
                        </div>
                        <span class="badge badge-green">{{ stats.models }} models</span>
                    </a>
                    
                    <!-- Step 4: Create Benchmark -->
                    <a href="/benchmarks" class="flex items-center gap-4 p-4 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-100 dark:border-amber-800 hover:shadow-md hover:border-amber-300 dark:hover:border-amber-600 transition-all group">
                        <div class="w-10 h-10 bg-amber-500 text-white rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0 group-hover:scale-110 transition-transform">4</div>
                        <div class="flex-grow">
                            <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">Create Benchmark</h3>
                            <p class="text-xs text-gray-600 dark:text-gray-400">Define Q/A pairs with gold answers for testing</p>
                        </div>
                        <span class="badge badge-yellow">{{ stats.benchmarks }} benchmarks</span>
                    </a>
                    
                    <!-- Step 5: Evaluate -->
                    <a href="/evaluations" class="flex items-center gap-4 p-4 rounded-lg bg-rose-50 dark:bg-rose-900/20 border border-rose-100 dark:border-rose-800 hover:shadow-md hover:border-rose-300 dark:hover:border-rose-600 transition-all group">
                        <div class="w-10 h-10 bg-rose-500 text-white rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0 group-hover:scale-110 transition-transform">5</div>
                        <div class="flex-grow">
                            <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">Evaluate</h3>
                            <p class="text-xs text-gray-600 dark:text-gray-400">Run benchmarks to get ROUGE scores on trained models</p>
                        </div>
                        <span class="badge badge-red">{{ stats.evals }} evals</span>
                    </a>
                    
                    <!-- Step 6: Extract -->
                    <a href="/meta" class="flex items-center gap-4 p-4 rounded-lg bg-cyan-50 dark:bg-cyan-900/20 border border-cyan-100 dark:border-cyan-800 hover:shadow-md hover:border-cyan-300 dark:hover:border-cyan-600 transition-all group">
                        <div class="w-10 h-10 bg-cyan-500 text-white rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0 group-hover:scale-110 transition-transform">6</div>
                        <div class="flex-grow">
                            <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">Extract</h3>
                            <p class="text-xs text-gray-600 dark:text-gray-400">Extract meta-features from completed experiments</p>
                        </div>
                        <span class="badge badge-blue">{{ stats.meta_features }} features</span>
                    </a>
                    
                    <!-- Step 7: Meta-Learn -->
                    <a href="/meta" class="flex items-center gap-4 p-4 rounded-lg bg-violet-50 dark:bg-violet-900/20 border border-violet-100 dark:border-violet-800 hover:shadow-md hover:border-violet-300 dark:hover:border-violet-600 transition-all group">
                        <div class="w-10 h-10 bg-violet-500 text-white rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0 group-hover:scale-110 transition-transform">7</div>
                        <div class="flex-grow">
                            <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">Meta-Learn</h3>
                            <p class="text-xs text-gray-600 dark:text-gray-400">Train predictor on meta-features to forecast performance. Requires 5+ experiments with ROUGE scores.</p>
                        </div>
                        {% if stats.meta_features >= 5 %}
                        <span class="badge badge-green">Ready</span>
                        {% else %}
                        <span class="badge badge-gray">{{ stats.meta_features }}/5 needed</span>
                        {% endif %}
                    </a>
                </div>
            </div>
        </div>
        {% endblock %}""",
    )
)

DATASETS_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Datasets - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="mb-6">
            <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Datasets</h1>
            <p class="text-gray-600 dark:text-gray-400">Upload and manage your training datasets</p>
        </div>
        
        <div class="card mb-6">
            <div class="card-header">
                <h2 class="font-semibold text-gray-800 dark:text-gray-200">Upload New Dataset</h2>
            </div>
            <div class="card-body">
                <form action="/datasets/upload" method="post" enctype="multipart/form-data" class="flex items-center gap-4">
                    <div class="flex-1">
                        <input type="file" name="file" accept=".csv" required
                            class="block w-full text-sm text-gray-500 dark:text-gray-400 file:mr-4 file:py-2.5 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100 file:cursor-pointer cursor-pointer">
                    </div>
                    <button type="submit" class="btn-primary">Upload CSV</button>
                </form>
            </div>
        </div>
        
        <div class="card">
            <div class="overflow-x-auto">
                <table class="w-full">
                    <thead>
                        <tr class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Filename</th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Columns</th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Rows</th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Uploaded</th>
                            <th class="px-6 py-3 text-right text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Actions</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        {% for dataset in datasets %}
                        <tr class="hover:bg-gray-50 dark:hover:bg-gray-700 dark:bg-gray-800 transition-colors">
                            <td class="px-6 py-4">
                                <span class="font-medium text-gray-900 dark:text-gray-100">{{ dataset.filename }}</span>
                            </td>
                            <td class="px-6 py-4">
                                <span class="text-sm text-gray-600 dark:text-gray-400">{{ dataset.columns | join(', ') | truncate(40) }}</span>
                            </td>
                            <td class="px-6 py-4">
                                <span class="badge badge-blue">{{ dataset.row_count }} rows</span>
                            </td>
                            <td class="px-6 py-4 text-sm text-gray-500 dark:text-gray-400"><span data-utc="{{ dataset.uploaded_at }}" data-format="date">{{ dataset.uploaded_at[:10] }}</span></td>
                            <td class="px-6 py-4">
                                <div class="flex items-center justify-end gap-2">
                                    <a href="/experiments/new/masked-lm?dataset_id={{ dataset.id }}" class="text-sm font-medium text-blue-600 hover:text-blue-800">MLM</a>
                                    <span class="text-gray-300">|</span>
                                    <a href="/experiments/new/causal-lm?dataset_id={{ dataset.id }}" class="text-sm font-medium text-emerald-600 hover:text-emerald-800">Causal</a>
                                    <span class="text-gray-300">|</span>
                                    <a href="/meta/probe?dataset_id={{ dataset.id }}" class="text-sm font-medium text-purple-600 hover:text-purple-800">Probe</a>
                                    <span class="text-gray-300">|</span>
                                    <a href="/meta/optimize?dataset_id={{ dataset.id }}" class="text-sm font-medium text-indigo-600 hover:text-indigo-800">Optimize</a>
                                    <span class="text-gray-300">|</span>
                                    <form action="/datasets/{{ dataset.id }}/delete" method="post" class="inline">
                                        <button type="submit" class="text-sm font-medium text-red-500 hover:text-red-700">Delete</button>
                                    </form>
                                </div>
                            </td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="5" class="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
                                <div class="flex flex-col items-center">
                                    <svg class="w-12 h-12 text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"></path></svg>
                                    <p>No datasets uploaded yet</p>
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endblock %}""",
    )
)

CONFIGS_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Configs - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="flex items-center justify-between mb-6">
            <div>
                <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Configurations</h1>
                <p class="text-gray-600 dark:text-gray-400">All saved training configurations</p>
            </div>
            <div class="flex items-center gap-3">
                <form id="upload-form" action="/configs/upload" method="post" enctype="multipart/form-data" class="flex items-center gap-2">
                    <input type="file" name="file" accept=".yaml,.yml" class="hidden" id="yaml-file-input" onchange="document.getElementById('upload-form').submit()">
                    <button type="button" onclick="document.getElementById('yaml-file-input').click()" class="btn-primary flex items-center gap-2">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                        Upload YAML
                    </button>
                </form>
            </div>
        </div>
        
        <!-- Filter/Search -->
        <div class="mb-4 flex items-center gap-4">
            <div class="flex-1">
                <input type="text" id="config-search" placeholder="Search by name or model..." class="form-input" onkeyup="filterConfigs()">
            </div>
            <select id="type-filter" class="form-select w-48" onchange="filterConfigs()">
                <option value="">All Types</option>
                <option value="causal_lm">Causal LM</option>
                <option value="masked_lm">Masked LM</option>
            </select>
        </div>
        
        <div class="card">
            <div class="overflow-x-auto">
                <table class="w-full" id="configs-table">
                    <thead>
                        <tr class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700" onclick="sortTable(0)">Name ↕</th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700" onclick="sortTable(1)">Type ↕</th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700" onclick="sortTable(2)">Model ↕</th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700" onclick="sortTable(3)">Created ↕</th>
                            <th class="px-4 py-3 text-center text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700" onclick="sortTable(4)">Experiments ↕</th>
                            <th class="px-4 py-3 text-center text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700" onclick="sortTable(5)">Avg Loss ↕</th>
                            <th class="px-4 py-3 text-center text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700" onclick="sortTable(6)">Avg ROUGE ↕</th>
                            <th class="px-4 py-3 text-right text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Actions</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100 dark:divide-gray-700" id="configs-tbody">
                        {% for config in configs %}
                        <tr class="hover:bg-gray-50 dark:hover:bg-gray-700 dark:bg-gray-800 transition-colors config-row" 
                            data-name="{{ config.name }}" 
                            data-type="{{ config.experiment_type }}" 
                            data-model="{{ config.config.model.pretrained_model_name }}">
                            <td class="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">
                                <a href="/configs/{{ config.id }}" class="hover:text-primary-600">{{ config.name }}</a>
                            </td>
                            <td class="px-4 py-3">
                                {% if config.experiment_type == 'causal_lm' %}
                                <span class="badge badge-green">Causal LM</span>
                                {% else %}
                                <span class="badge badge-blue">Masked LM</span>
                                {% endif %}
                            </td>
                            <td class="px-4 py-3 text-sm text-gray-600 dark:text-gray-400 font-mono">{{ config.config.model.pretrained_model_name | truncate(30) }}</td>
                            <td class="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                                <span data-utc="{{ config.created_at }}">{{ config.created_at }}</span>
                            </td>
                            <td class="px-4 py-3 text-center">
                                {% if config.experiment_count > 0 %}
                                <span class="badge badge-gray">{{ config.experiment_count }}</span>
                                {% else %}
                                <span class="text-gray-400">-</span>
                                {% endif %}
                            </td>
                            <td class="px-4 py-3 text-center text-sm">
                                {% if config.avg_train_loss is not none %}
                                <span class="font-mono text-amber-600 dark:text-amber-400">{{ "%.4f"|format(config.avg_train_loss) }}</span>
                                {% else %}
                                <span class="text-gray-400">-</span>
                                {% endif %}
                            </td>
                            <td class="px-4 py-3 text-center text-sm">
                                {% if config.avg_bleu is not none %}
                                <span class="font-mono text-emerald-600 dark:text-emerald-400">{{ "%.2f"|format(config.avg_bleu) }}</span>
                                {% else %}
                                <span class="text-gray-400">-</span>
                                {% endif %}
                            </td>
                            <td class="px-4 py-3 text-right">
                                <div class="flex items-center justify-end gap-3">
                                    <a href="/configs/{{ config.id }}" class="text-sm font-medium text-primary-600 hover:text-primary-800">View</a>
                                    <a href="/configs/{{ config.id }}/edit" class="text-sm font-medium text-amber-600 hover:text-amber-800">Edit</a>
                                    <form action="/configs/{{ config.id }}/delete" method="post" class="inline" onsubmit="return confirm('Delete this config?')">
                                        <button type="submit" class="text-sm font-medium text-red-500 hover:text-red-700">Delete</button>
                                    </form>
                                </div>
                            </td>
                        </tr>
                        {% else %}
                        <tr id="no-configs-row">
                            <td colspan="8" class="px-6 py-12 text-center text-gray-500 dark:text-gray-400">No configurations found. Upload a YAML file to get started.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        
        <script>
        let sortDirection = {};
        
        function sortTable(colIndex) {
            const table = document.getElementById('configs-table');
            const tbody = document.getElementById('configs-tbody');
            const rows = Array.from(tbody.querySelectorAll('.config-row'));
            
            sortDirection[colIndex] = !sortDirection[colIndex];
            const dir = sortDirection[colIndex] ? 1 : -1;
            
            rows.sort((a, b) => {
                let aVal = a.cells[colIndex].textContent.trim();
                let bVal = b.cells[colIndex].textContent.trim();
                
                // Handle numeric columns (experiments, loss, bleu)
                if (colIndex >= 4 && colIndex <= 6) {
                    aVal = aVal === '-' ? -Infinity : parseFloat(aVal);
                    bVal = bVal === '-' ? -Infinity : parseFloat(bVal);
                    return (aVal - bVal) * dir;
                }
                
                return aVal.localeCompare(bVal) * dir;
            });
            
            rows.forEach(row => tbody.appendChild(row));
        }
        
        function filterConfigs() {
            const search = document.getElementById('config-search').value.toLowerCase();
            const typeFilter = document.getElementById('type-filter').value;
            const rows = document.querySelectorAll('.config-row');
            
            rows.forEach(row => {
                const name = row.dataset.name.toLowerCase();
                const model = row.dataset.model.toLowerCase();
                const type = row.dataset.type;
                
                const matchesSearch = name.includes(search) || model.includes(search);
                const matchesType = !typeFilter || type === typeFilter;
                
                row.style.display = matchesSearch && matchesType ? '' : 'none';
            });
        }
        </script>
        {% endblock %}""",
    )
)

CONFIG_DETAIL_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Config - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="mb-6">
            <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-3">
                    <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">{{ config.name }}</h1>
                    {% if config.experiment_type == 'causal_lm' %}
                    <span class="badge badge-green">Causal LM</span>
                    {% else %}
                    <span class="badge badge-blue">Masked LM</span>
                    {% endif %}
                </div>
                <a href="/configs" class="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white">&larr; Back to Configs</a>
            </div>
            <div class="flex items-center justify-between">
                <div class="text-sm text-gray-500 dark:text-gray-400">
                    Created: <span data-utc="{{ config.created_at }}">{{ config.created_at }}</span>
                    <span class="mx-2">•</span>
                    ID: <code class="text-xs bg-gray-100 dark:bg-gray-700 px-1 rounded">{{ config.id }}</code>
                </div>
                <div class="flex items-center gap-3">
                    <a href="/configs/{{ config.id }}/edit" class="btn-primary flex items-center gap-2">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path></svg>
                        Edit (Copy)
                    </a>
                    <form action="/configs/{{ config.id }}/delete" method="post" class="inline" onsubmit="return confirm('Delete this config?')">
                        <button type="submit" class="btn-danger">Delete</button>
                    </form>
                </div>
            </div>
        </div>
        
        <!-- Config Summary Cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div class="metric-card">
                <div class="metric-label">Model</div>
                <div class="text-sm font-mono text-gray-700 dark:text-gray-300 truncate">{{ config.config.model.pretrained_model_name }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Learning Rate</div>
                <div class="metric-value">{{ config.config.training.learning_rate }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Epochs</div>
                <div class="metric-value">{{ config.config.training.num_train_epochs }}</div>
            </div>
        </div>
        
        <!-- Config Sections -->
        <div class="space-y-4">
            <!-- Data Config -->
            <div class="section-card">
                <div class="section-header">
                    <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"></path></svg>
                    <h2 class="section-title">Data Configuration</h2>
                </div>
                <div class="section-body">
                    <pre class="bg-gray-900 text-gray-100 p-4 rounded-lg text-sm font-mono overflow-x-auto">{{ config.config.data | tojson(indent=2) }}</pre>
                </div>
            </div>
            
            <!-- Model Config -->
            <div class="section-card">
                <div class="section-header">
                    <svg class="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                    <h2 class="section-title">Model Configuration</h2>
                </div>
                <div class="section-body">
                    <pre class="bg-gray-900 text-gray-100 p-4 rounded-lg text-sm font-mono overflow-x-auto">{{ config.config.model | tojson(indent=2) }}</pre>
                </div>
            </div>
            
            <!-- Training Config -->
            <div class="section-card">
                <div class="section-header">
                    <svg class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                    <h2 class="section-title">Training Configuration</h2>
                </div>
                <div class="section-body">
                    <pre class="bg-gray-900 text-gray-100 p-4 rounded-lg text-sm font-mono overflow-x-auto">{{ config.config.training | tojson(indent=2) }}</pre>
                </div>
            </div>
            
            {% if config.experiment_type == 'causal_lm' and config.config.peft %}
            <!-- PEFT Config -->
            <div class="section-card">
                <div class="section-header">
                    <svg class="w-5 h-5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"></path></svg>
                    <h2 class="section-title">PEFT / LoRA Configuration</h2>
                </div>
                <div class="section-body">
                    <pre class="bg-gray-900 text-gray-100 p-4 rounded-lg text-sm font-mono overflow-x-auto">{{ config.config.peft | tojson(indent=2) }}</pre>
                </div>
            </div>
            {% endif %}
        </div>
        {% endblock %}""",
    )
)

CONFIG_EDIT_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Edit Config - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="max-w-4xl mx-auto">
            <div class="mb-6">
                <div class="flex items-center justify-between mb-4">
                    <div class="flex items-center gap-3">
                        <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Edit Configuration</h1>
                        {% if config.experiment_type == 'causal_lm' %}
                        <span class="badge badge-green">Causal LM</span>
                        {% else %}
                        <span class="badge badge-blue">Masked LM</span>
                        {% endif %}
                    </div>
                    <a href="/configs/{{ config.id }}" class="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white">&larr; Back to Config</a>
                </div>
                <p class="text-gray-600 dark:text-gray-400">
                    Editing <span class="font-medium text-gray-900 dark:text-gray-100">{{ config.name }}</span> - saves as new config
                </p>
            </div>
            
            <form action="/configs/{{ config.id }}/edit" method="post" class="space-y-6">
                <!-- New Config Name -->
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"></path></svg>
                        <h2 class="section-title">New Config Name</h2>
                    </div>
                    <div class="section-body">
                        <div class="form-group">
                            <label class="form-label">Name for the new config</label>
                            <input type="text" name="new_name" value="{{ config.name }}-copy" class="form-input" placeholder="my-config-v2">
                            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Leave empty to auto-generate a friendly name</p>
                        </div>
                    </div>
                </div>
                
                {% if config.experiment_type == 'causal_lm' %}
                <!-- Causal LM Config -->
                
                <!-- Data Config -->
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"></path></svg>
                        <h2 class="section-title">Data Configuration</h2>
                    </div>
                    <div class="section-body space-y-4">
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div class="form-group">
                                <label class="form-label">Question Field</label>
                                <input type="text" name="question_field" value="{{ config.config.data.question_field }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Answer Field</label>
                                <input type="text" name="answer_field" value="{{ config.config.data.answer_field }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Validation Split</label>
                                <input type="number" name="validation_split" value="{{ config.config.data.validation_split }}" step="0.05" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Max Length</label>
                                <input type="number" name="max_length" value="{{ config.config.data.max_length }}" class="form-input">
                            </div>
                        </div>
                        <div class="form-group">
                            <label class="form-label">System Prompt</label>
                            <textarea name="system_prompt" rows="2" class="form-textarea">{{ config.config.data.system_prompt }}</textarea>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Template</label>
                            <textarea name="template" rows="4" class="form-textarea font-mono text-xs">{{ config.config.data.template }}</textarea>
                        </div>
                    </div>
                </div>
                
                <!-- Model Config -->
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                        <h2 class="section-title">Model Configuration</h2>
                    </div>
                    <div class="section-body">
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div class="form-group">
                                <label class="form-label">Pretrained Model</label>
                                <input type="text" name="pretrained_model_name" value="{{ config.config.model.pretrained_model_name }}" class="form-input font-mono">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Pad Token Override</label>
                                <input type="text" name="pad_token_override" value="{{ config.config.model.pad_token_override or '' }}" class="form-input font-mono">
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- PEFT Config -->
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"></path></svg>
                        <h2 class="section-title">PEFT / LoRA Configuration</h2>
                    </div>
                    <div class="section-body">
                        <div class="flex items-center gap-3 mb-4">
                            <input type="checkbox" name="peft_enabled" id="peft_enabled" class="form-checkbox" {% if config.config.peft.enabled %}checked{% endif %}>
                            <label for="peft_enabled" class="text-sm text-gray-700 dark:text-gray-300">Enable PEFT/LoRA</label>
                        </div>
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div class="form-group">
                                <label class="form-label">LoRA Rank (r)</label>
                                <input type="number" name="peft_r" value="{{ config.config.peft.r }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">LoRA Alpha</label>
                                <input type="number" name="peft_lora_alpha" value="{{ config.config.peft.lora_alpha }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">LoRA Dropout</label>
                                <input type="number" name="peft_lora_dropout" value="{{ config.config.peft.lora_dropout }}" step="0.01" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Bias</label>
                                <select name="peft_bias" class="form-select">
                                    <option value="none" {% if config.config.peft.bias == 'none' %}selected{% endif %}>none</option>
                                    <option value="lora_only" {% if config.config.peft.bias == 'lora_only' %}selected{% endif %}>lora_only</option>
                                    <option value="all" {% if config.config.peft.bias == 'all' %}selected{% endif %}>all</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-group mt-4">
                            <label class="form-label">Target Modules (comma-separated)</label>
                            <input type="text" name="peft_target_modules" value="{{ config.config.peft.target_modules | join(',') }}" class="form-input font-mono">
                        </div>
                    </div>
                </div>
                
                <!-- Training Config -->
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                        <h2 class="section-title">Training Configuration</h2>
                    </div>
                    <div class="section-body">
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div class="form-group">
                                <label class="form-label">Epochs</label>
                                <input type="number" name="num_train_epochs" value="{{ config.config.training.num_train_epochs }}" step="0.5" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Learning Rate</label>
                                <input type="text" name="learning_rate" value="{{ config.config.training.learning_rate }}" class="form-input font-mono">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Batch Size</label>
                                <input type="number" name="per_device_train_batch_size" value="{{ config.config.training.per_device_train_batch_size }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Gradient Accumulation</label>
                                <input type="number" name="gradient_accumulation_steps" value="{{ config.config.training.gradient_accumulation_steps }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Weight Decay</label>
                                <input type="number" name="weight_decay" value="{{ config.config.training.weight_decay }}" step="0.001" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Warmup Ratio</label>
                                <input type="number" name="warmup_ratio" value="{{ config.config.training.warmup_ratio }}" step="0.01" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">LR Scheduler</label>
                                <select name="lr_scheduler_type" class="form-select">
                                    <option value="cosine" {% if config.config.training.lr_scheduler_type == 'cosine' %}selected{% endif %}>cosine</option>
                                    <option value="linear" {% if config.config.training.lr_scheduler_type == 'linear' %}selected{% endif %}>linear</option>
                                    <option value="constant" {% if config.config.training.lr_scheduler_type == 'constant' %}selected{% endif %}>constant</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label class="form-label">Max Steps</label>
                                <input type="number" name="max_steps" value="{{ config.config.training.max_steps }}" class="form-input">
                            </div>
                        </div>
                        <div class="grid grid-cols-3 gap-4 mt-4">
                            <div class="flex items-center gap-2">
                                <input type="checkbox" name="gradient_checkpointing" id="gradient_checkpointing" class="form-checkbox" {% if config.config.training.gradient_checkpointing %}checked{% endif %}>
                                <label for="gradient_checkpointing" class="text-sm text-gray-700 dark:text-gray-300">Gradient Checkpointing</label>
                            </div>
                            <div class="flex items-center gap-2">
                                <input type="checkbox" name="fp16" id="fp16" class="form-checkbox" {% if config.config.training.fp16 %}checked{% endif %}>
                                <label for="fp16" class="text-sm text-gray-700 dark:text-gray-300">FP16</label>
                            </div>
                            <div class="flex items-center gap-2">
                                <input type="checkbox" name="bf16" id="bf16" class="form-checkbox" {% if config.config.training.bf16 %}checked{% endif %}>
                                <label for="bf16" class="text-sm text-gray-700 dark:text-gray-300">BF16</label>
                            </div>
                        </div>
                        <!-- Early Stopping -->
                        <div class="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                            <div class="form-group">
                                <label class="form-label">Early Stopping Patience</label>
                                <input type="number" name="early_stopping_patience" value="{{ config.config.training.early_stopping_patience if config.config.training.early_stopping_patience else '' }}" placeholder="e.g. 3" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Early Stopping Metric</label>
                                <select name="early_stopping_metric" class="form-select">
                                    <option value="eval_loss" {% if not config.config.training.early_stopping_metric or config.config.training.early_stopping_metric == 'eval_loss' %}selected{% endif %}>eval_loss</option>
                                    <option value="eval_accuracy" {% if config.config.training.early_stopping_metric == 'eval_accuracy' %}selected{% endif %}>eval_accuracy</option>
                                    <option value="eval_f1" {% if config.config.training.early_stopping_metric == 'eval_f1' %}selected{% endif %}>eval_f1</option>
                                    <option value="eval_perplexity" {% if config.config.training.early_stopping_metric == 'eval_perplexity' %}selected{% endif %}>eval_perplexity</option>
                                </select>
                            </div>
                            <div class="flex items-center gap-2 pt-6">
                                <input type="checkbox" name="early_stopping_greater_is_better" id="early_stopping_greater_is_better_edit" class="form-checkbox" {% if config.config.training.early_stopping_greater_is_better %}checked{% endif %}>
                                <label for="early_stopping_greater_is_better_edit" class="text-sm text-gray-700 dark:text-gray-300">Greater is Better</label>
                            </div>
                        </div>
                    </div>
                </div>
                
                {% else %}
                <!-- Masked LM Config -->
                
                <!-- Data Config -->
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"></path></svg>
                        <h2 class="section-title">Data Configuration</h2>
                    </div>
                    <div class="section-body">
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div class="form-group md:col-span-2">
                                <label class="form-label">Text Fields (comma-separated)</label>
                                <input type="text" name="text_fields" value="{{ config.config.data.text_fields | join(',') }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Separator</label>
                                <input type="text" name="separator" value="{{ config.config.data.separator | replace('\n', '\\n') }}" class="form-input font-mono">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Max Length</label>
                                <input type="number" name="max_length" value="{{ config.config.data.max_length }}" class="form-input">
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Model Config -->
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                        <h2 class="section-title">Model Configuration</h2>
                    </div>
                    <div class="section-body">
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div class="form-group md:col-span-2">
                                <label class="form-label">Pretrained Model</label>
                                <input type="text" name="pretrained_model_name" value="{{ config.config.model.pretrained_model_name }}" class="form-input font-mono">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Freeze Encoder Layers</label>
                                <input type="number" name="freeze_encoder_layers" value="{{ config.config.model.freeze_encoder_layers }}" min="0" class="form-input">
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Training Config -->
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                        <h2 class="section-title">Training Configuration</h2>
                    </div>
                    <div class="section-body">
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div class="form-group">
                                <label class="form-label">Epochs</label>
                                <input type="number" name="num_train_epochs" value="{{ config.config.training.num_train_epochs }}" step="0.5" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Learning Rate</label>
                                <input type="text" name="learning_rate" value="{{ config.config.training.learning_rate }}" class="form-input font-mono">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Batch Size</label>
                                <input type="number" name="per_device_train_batch_size" value="{{ config.config.training.per_device_train_batch_size }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Weight Decay</label>
                                <input type="number" name="weight_decay" value="{{ config.config.training.weight_decay }}" step="0.001" class="form-input">
                            </div>
                        </div>
                        <!-- Early Stopping -->
                        <div class="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                            <div class="form-group">
                                <label class="form-label">Early Stopping Patience</label>
                                <input type="number" name="early_stopping_patience" value="{{ config.config.training.early_stopping_patience if config.config.training.early_stopping_patience else '' }}" placeholder="e.g. 3" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Early Stopping Metric</label>
                                <select name="early_stopping_metric" class="form-select">
                                    <option value="eval_loss" {% if not config.config.training.early_stopping_metric or config.config.training.early_stopping_metric == 'eval_loss' %}selected{% endif %}>eval_loss</option>
                                    <option value="eval_accuracy" {% if config.config.training.early_stopping_metric == 'eval_accuracy' %}selected{% endif %}>eval_accuracy</option>
                                    <option value="eval_f1" {% if config.config.training.early_stopping_metric == 'eval_f1' %}selected{% endif %}>eval_f1</option>
                                    <option value="eval_perplexity" {% if config.config.training.early_stopping_metric == 'eval_perplexity' %}selected{% endif %}>eval_perplexity</option>
                                </select>
                            </div>
                            <div class="flex items-center gap-2 pt-6">
                                <input type="checkbox" name="early_stopping_greater_is_better" id="early_stopping_greater_is_better_mlm_edit" class="form-checkbox" {% if config.config.training.early_stopping_greater_is_better %}checked{% endif %}>
                                <label for="early_stopping_greater_is_better_mlm_edit" class="text-sm text-gray-700 dark:text-gray-300">Greater is Better</label>
                            </div>
                        </div>
                    </div>
                </div>
                {% endif %}
                
                <!-- Submit -->
                <div class="flex items-center justify-end gap-4">
                    <a href="/configs/{{ config.id }}" class="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white">Cancel</a>
                    <button type="submit" class="btn-success flex items-center gap-2">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"></path></svg>
                        Save as New Config
                    </button>
                </div>
            </form>
        </div>
        {% endblock %}""",
    )
)

NEW_MASKED_LM_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}New Masked LM Experiment{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="max-w-4xl mx-auto">
            <div class="mb-6">
                <div class="flex items-center gap-3 mb-2">
                    <span class="badge badge-blue">Masked LM</span>
                    <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">New Experiment</h1>
                </div>
                <p class="text-gray-600 dark:text-gray-400">
                    Dataset: <span class="font-medium text-gray-900 dark:text-gray-100">{{ dataset.filename }}</span> 
                    <span class="text-gray-400">•</span> {{ dataset.row_count }} rows 
                    <span class="text-gray-400">•</span> Columns: {{ dataset.columns | join(', ') }}
                </p>
            </div>
            
            <form action="/experiments/masked-lm" method="post" class="space-y-6" id="experiment-form">
                <input type="hidden" name="dataset_id" value="{{ dataset.id }}">
                <input type="hidden" name="config_id" id="config-id-input" value="">
                
                <!-- Config Selector -->
                {% if configs %}
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                        <h2 class="section-title">Select Configuration</h2>
                    </div>
                    <div class="section-body">
                        <div class="flex items-center gap-4">
                            <div class="form-group flex-1">
                                <label class="form-label">Use an existing saved configuration</label>
                                <select id="config-selector" class="form-select" onchange="handleConfigSelect(this)">
                                    <option value="">-- Create new config from form --</option>
                                    {% for config in configs %}
                                    <option value="{{ config.id }}">{{ config.name }} ({{ config.config.model.pretrained_model_name | truncate(30) }})</option>
                                    {% endfor %}
                                </select>
                            </div>
                        </div>
                        <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">Select an existing config to use it directly, or leave empty to create a new config from the form below.</p>
                    </div>
                </div>
                {% endif %}
                
                <!-- Data Config -->
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"></path></svg>
                        <h2 class="section-title">Data Configuration</h2>
                    </div>
                    <div class="section-body">
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div class="form-group md:col-span-2">
                                <label class="form-label flex items-center gap-1">Text Fields <span class="text-gray-400 font-normal">(comma-separated)</span>
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">CSV columns to concatenate for training text. Order matters for input format.</span></span>
                                </label>
                                <input type="text" name="text_fields" value="question,answer" class="form-input" placeholder="question,answer">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Separator
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">String inserted between concatenated fields. Use \\n for newline.</span></span>
                                </label>
                                <input type="text" name="separator" value="\\n\\n" class="form-input font-mono">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Validation Split
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Fraction of data reserved for validation. Values: 0.05-0.5</span></span>
                                </label>
                                <input type="number" name="validation_split" value="0.2" step="0.05" min="0.05" max="0.5" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Random Seed
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Random seed for reproducible train/val splits. Use same seed to reproduce results.</span></span>
                                </label>
                                <input type="number" name="seed" value="42" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Max Token Length
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Max tokens per sample. Longer sequences are truncated. Higher = more memory.</span></span>
                                </label>
                                <input type="number" name="max_length" value="256" class="form-input">
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Model Config -->
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                        <h2 class="section-title">Model Configuration</h2>
                    </div>
                    <div class="section-body">
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div class="form-group md:col-span-2">
                                <label class="form-label flex items-center gap-1">Pretrained Model
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">HuggingFace model ID or local path. Examples: distilbert-base-uncased, bert-base-cased</span></span>
                                </label>
                                <input type="text" name="pretrained_model_name" value="distilbert-base-uncased" class="form-input font-mono">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Freeze Encoder Layers
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Number of encoder layers to freeze (0 = train all). Freezing reduces trainable params. Range: 0-6 for DistilBERT.</span></span>
                                </label>
                                <input type="number" name="freeze_encoder_layers" value="0" min="0" max="6" class="form-input">
                            </div>
                            <div class="form-group flex items-center gap-3 pt-2">
                                <input type="checkbox" name="freeze_embedding" id="freeze_embedding" class="form-checkbox">
                                <label for="freeze_embedding" class="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-1">Freeze Embedding Layer
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Keep embedding weights fixed during training. Useful to prevent catastrophic forgetting.</span></span>
                                </label>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Training Config -->
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                        <h2 class="section-title">Training Configuration</h2>
                    </div>
                    <div class="section-body">
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Epochs
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Number of complete passes through training data. More epochs = longer training.</span></span>
                                </label>
                                <input type="number" name="num_train_epochs" value="3" step="0.5" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Learning Rate
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Step size for optimizer. Typical range: 1e-5 to 1e-3. Lower = stable but slow, higher = faster but may diverge.</span></span>
                                </label>
                                <input type="text" name="learning_rate" value="5e-5" class="form-input font-mono">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Train Batch Size
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Samples per device per training step. Larger = faster but more memory. Reduce if OOM.</span></span>
                                </label>
                                <input type="number" name="per_device_train_batch_size" value="8" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Eval Batch Size
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Samples per device during evaluation. Can be larger than train batch since no gradients stored.</span></span>
                                </label>
                                <input type="number" name="per_device_eval_batch_size" value="8" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Weight Decay
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">L2 regularization factor. Helps prevent overfitting. Typical: 0.0-0.1</span></span>
                                </label>
                                <input type="number" name="weight_decay" value="0.01" step="0.01" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Warmup Ratio
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Fraction of training steps for learning rate warmup. Gradually increases LR from 0. Typical: 0.0-0.1</span></span>
                                </label>
                                <input type="number" name="warmup_ratio" value="0.0" step="0.01" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Gradient Accum Steps
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Accumulate gradients over N steps before update. Effective batch = batch_size * accum_steps. Use to simulate larger batches.</span></span>
                                </label>
                                <input type="number" name="gradient_accumulation_steps" value="1" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Max Steps
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Hard limit on training steps. Set to -1 to use epochs instead. Overrides epochs if positive.</span></span>
                                </label>
                                <input type="number" name="max_steps" value="-1" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Logging Steps
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Log training metrics every N steps. Lower = more detailed logs but slightly slower.</span></span>
                                </label>
                                <input type="number" name="logging_steps" value="10" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Eval Steps
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Run evaluation on validation set every N steps. More frequent = better monitoring but slower training.</span></span>
                                </label>
                                <input type="number" name="eval_steps" value="50" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Save Steps
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Save model checkpoint every N steps. Checkpoints allow resuming and selecting best model.</span></span>
                                </label>
                                <input type="number" name="save_steps" value="200" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Save Total Limit
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Max checkpoints to keep on disk. Older checkpoints are deleted. Saves disk space.</span></span>
                                </label>
                                <input type="number" name="save_total_limit" value="2" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Early Stop Patience
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Stop training after N evals without improvement. Leave blank to disable. Prevents overfitting.</span></span>
                                </label>
                                <input type="number" name="early_stopping_patience" value="" placeholder="e.g. 3" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Early Stop Metric
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Metric to monitor for early stopping. eval_loss is most common for MLM tasks.</span></span>
                                </label>
                                <select name="early_stopping_metric" id="early_stopping_metric_mlm" class="form-select font-mono">
                                    <option value="eval_loss" selected>eval_loss</option>
                                    <option value="eval_accuracy">eval_accuracy</option>
                                    <option value="eval_f1">eval_f1</option>
                                    <option value="eval_perplexity">eval_perplexity</option>
                                </select>
                            </div>
                            <div class="form-group flex items-center gap-3 pt-6">
                                <input type="checkbox" name="early_stopping_greater_is_better" id="early_stopping_greater_is_better_mlm" class="form-checkbox">
                                <label for="early_stopping_greater_is_better_mlm" class="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-1">Greater is Better
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Check if higher metric values are better. True for accuracy/F1, false for loss.</span></span>
                                </label>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="flex justify-end gap-3">
                    <a href="/datasets" class="px-4 py-2 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-100 rounded-lg transition-all">Cancel</a>
                    <button type="submit" class="btn-primary px-8">Start Training</button>
                </div>
            </form>
        </div>
        
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Auto-select greater is better based on metric
            const metricSelect = document.getElementById('early_stopping_metric_mlm');
            const greaterCheckbox = document.getElementById('early_stopping_greater_is_better_mlm');
            if (metricSelect && greaterCheckbox) {
                metricSelect.addEventListener('change', function() {
                    const greaterIsBetter = ['eval_accuracy', 'eval_f1'].includes(this.value);
                    greaterCheckbox.checked = greaterIsBetter;
                });
            }
            
        });
        
        function handleConfigSelect(select) {
            const configIdInput = document.getElementById('config-id-input');
            const formSections = document.querySelectorAll('.section-card:not(:first-of-type)');
            
            if (select.value) {
                // Config selected - hide form sections and set config_id
                configIdInput.value = select.value;
                formSections.forEach(section => {
                    section.style.opacity = '0.5';
                    section.querySelectorAll('input, select, textarea').forEach(el => el.disabled = true);
                });
            } else {
                // No config selected - show form sections
                configIdInput.value = '';
                formSections.forEach(section => {
                    section.style.opacity = '1';
                    section.querySelectorAll('input, select, textarea').forEach(el => el.disabled = false);
                });
            }
        }
        </script>
        {% endblock %}""",
    )
)

NEW_CAUSAL_LM_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}New Causal LM Experiment{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="max-w-4xl mx-auto">
            <div class="mb-6">
                <div class="flex items-center gap-3 mb-2">
                    <span class="badge badge-green">Causal LM</span>
                    <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">New Experiment</h1>
                </div>
                <p class="text-gray-600 dark:text-gray-400">
                    Dataset: <span class="font-medium text-gray-900 dark:text-gray-100">{{ dataset.filename }}</span> 
                    <span class="text-gray-400">•</span> {{ dataset.row_count }} rows 
                    <span class="text-gray-400">•</span> Columns: {{ dataset.columns | join(', ') }}
                </p>
            </div>
            
            <form action="/experiments/causal-lm" method="post" class="space-y-6" id="experiment-form">
                <input type="hidden" name="dataset_id" value="{{ dataset.id }}">
                <input type="hidden" name="config_id" id="config-id-input" value="">
                
                <!-- Config Selector -->
                {% if configs %}
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                        <h2 class="section-title">Select Configuration</h2>
                    </div>
                    <div class="section-body">
                        <div class="flex items-center gap-4">
                            <div class="form-group flex-1">
                                <label class="form-label">Use an existing saved configuration</label>
                                <select id="config-selector" class="form-select" onchange="handleConfigSelect(this)">
                                    <option value="">-- Create new config from form --</option>
                                    {% for config in configs %}
                                    <option value="{{ config.id }}">{{ config.name }} ({{ config.config.model.pretrained_model_name | truncate(30) }})</option>
                                    {% endfor %}
                                </select>
                            </div>
                        </div>
                        <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">Select an existing config to use it directly, or leave empty to create a new config from the form below.</p>
                    </div>
                </div>
                {% endif %}
                
                <!-- Data Config -->
                <div class="section-card" id="form-config-section">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"></path></svg>
                        <h2 class="section-title">Data Configuration</h2>
                    </div>
                    <div class="section-body space-y-4">
                        <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Question Field
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">CSV column name containing the input questions/prompts.</span></span>
                                </label>
                                <input type="text" name="question_field" value="question" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Answer Field
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">CSV column name containing the expected answers/responses.</span></span>
                                </label>
                                <input type="text" name="answer_field" value="answer" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Validation Split
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Fraction of data reserved for validation. Values: 0.05-0.5</span></span>
                                </label>
                                <input type="number" name="validation_split" value="0.2" step="0.05" min="0.05" max="0.5" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Random Seed
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Random seed for reproducible train/val splits.</span></span>
                                </label>
                                <input type="number" name="seed" value="42" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Max Length
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Max tokens per sample including prompt and response. Higher = more memory.</span></span>
                                </label>
                                <input type="number" name="max_length" value="512" class="form-input">
                            </div>
                        </div>
                        <div class="form-group">
                            <label class="form-label flex items-center gap-1">System Prompt
                                <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">System message prepended to each sample. Defines the assistant persona and behavior.</span></span>
                            </label>
                            <textarea name="system_prompt" rows="2" class="form-textarea">You are an AI assistant.</textarea>
                        </div>
                        <div class="form-group">
                            <label class="form-label flex items-center gap-1">Chat Template
                                <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Chat format template using {system_prompt}, {question}, {answer} placeholders. Must match model's expected format.</span></span>
                            </label>
                            <textarea name="template" rows="4" class="form-textarea text-xs"><|system|>
{system_prompt}
</s>
<|user|>
{question}
</s>
<|assistant|>
{answer}
</s></textarea>
                        </div>
                    </div>
                </div>
                
                <!-- Model Config -->
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                        <h2 class="section-title">Model Configuration</h2>
                    </div>
                    <div class="section-body">
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div class="form-group md:col-span-2">
                                <label class="form-label flex items-center gap-1">Pretrained Model
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">HuggingFace model ID or local path. Examples: TinyLlama/TinyLlama-1.1B-Chat-v1.0, mistralai/Mistral-7B-v0.1</span></span>
                                </label>
                                <input type="text" name="pretrained_model_name" value="TinyLlama/TinyLlama-1.1B-Chat-v1.0" class="form-input font-mono text-sm">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Pad Token Override
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Token to use for padding. Required for models without a default pad token. Common: &lt;/s&gt;, &lt;eos&gt;</span></span>
                                </label>
                                <input type="text" name="pad_token_override" value="</s>" class="form-input font-mono">
                            </div>
                            <div class="form-group flex items-center gap-3 pt-2">
                                <input type="checkbox" name="trust_remote_code" id="trust_remote_code" class="form-checkbox">
                                <label for="trust_remote_code" class="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-1">Trust Remote Code
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Allow executing custom code from model repo. Required for some models. Security risk for untrusted sources.</span></span>
                                </label>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- PEFT Config -->
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"></path></svg>
                        <h2 class="section-title">LoRA / PEFT Configuration</h2>
                    </div>
                    <div class="section-body">
                        <div class="flex items-center gap-3 mb-4 pb-4 border-b border-gray-100 dark:border-gray-700">
                            <input type="checkbox" name="peft_enabled" id="peft_enabled" checked class="form-checkbox">
                            <label for="peft_enabled" class="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-1">Enable LoRA Adapters
                                <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Use Low-Rank Adaptation instead of full fine-tuning. Much faster and uses less memory. Recommended for most cases.</span></span>
                            </label>
                        </div>
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Rank (r)
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">LoRA rank - dimensionality of adapter matrices. Higher = more trainable params. Common: 4, 8, 16, 32, 64</span></span>
                                </label>
                                <input type="number" name="peft_r" value="64" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Alpha
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">LoRA scaling factor. Controls adapter strength. Often set to 2x the rank value.</span></span>
                                </label>
                                <input type="number" name="peft_lora_alpha" value="128" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Dropout
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Dropout probability for LoRA layers. Helps prevent overfitting. Range: 0.0-0.1</span></span>
                                </label>
                                <input type="number" name="peft_lora_dropout" value="0.01" step="0.01" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Bias
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Which bias params to train. none: no biases, lora_only: only LoRA biases, all: all biases</span></span>
                                </label>
                                <select name="peft_bias" class="form-select">
                                    <option value="none" selected>none</option>
                                    <option value="lora_only">lora_only</option>
                                    <option value="all">all</option>
                                </select>
                            </div>
                            <div class="form-group md:col-span-4">
                                <label class="form-label flex items-center gap-1">Target Modules
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Model layers to apply LoRA. Common attention layers: q_proj, k_proj, v_proj, o_proj. Add gate_proj, up_proj, down_proj for MLP.</span></span>
                                </label>
                                <input type="text" name="peft_target_modules" value="q_proj,k_proj,v_proj,o_proj" class="form-input font-mono text-sm">
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Training Config -->
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                        <h2 class="section-title">Training Configuration</h2>
                    </div>
                    <div class="section-body">
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Epochs
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Number of complete passes through training data.</span></span>
                                </label>
                                <input type="number" name="num_train_epochs" value="3" step="0.5" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Learning Rate
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Step size for optimizer. For LoRA: 1e-4 to 2e-4 typical. Full fine-tune: 1e-5 to 5e-5</span></span>
                                </label>
                                <input type="text" name="learning_rate" value="1e-4" class="form-input font-mono">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Train Batch Size
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Samples per device per step. Small for LLMs (1-4). Use gradient accumulation for larger effective batch.</span></span>
                                </label>
                                <input type="number" name="per_device_train_batch_size" value="1" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Eval Batch Size
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Samples per device during evaluation. Can be slightly larger than train batch.</span></span>
                                </label>
                                <input type="number" name="per_device_eval_batch_size" value="1" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Weight Decay
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">L2 regularization factor. Often 0.0 for LoRA, 0.01-0.1 for full fine-tune.</span></span>
                                </label>
                                <input type="number" name="weight_decay" value="0.0" step="0.01" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Warmup Ratio
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Fraction of training for LR warmup. Gradually increases LR from 0. Typical: 0.03-0.1</span></span>
                                </label>
                                <input type="number" name="warmup_ratio" value="0.03" step="0.01" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Gradient Accum Steps
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Accumulate gradients over N steps. Effective batch = batch_size * accum_steps. Use to simulate larger batches on limited memory.</span></span>
                                </label>
                                <input type="number" name="gradient_accumulation_steps" value="8" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">LR Scheduler
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Learning rate schedule. cosine: smooth decay, linear: steady decay, constant: no decay</span></span>
                                </label>
                                <select name="lr_scheduler_type" class="form-select">
                                    <option value="cosine" selected>cosine</option>
                                    <option value="linear">linear</option>
                                    <option value="constant">constant</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Logging Steps
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Log training metrics every N steps.</span></span>
                                </label>
                                <input type="number" name="logging_steps" value="5" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Eval Steps
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Run evaluation on validation set every N steps.</span></span>
                                </label>
                                <input type="number" name="eval_steps" value="20" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Save Steps
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Save model checkpoint every N steps.</span></span>
                                </label>
                                <input type="number" name="save_steps" value="100" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Max Steps
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Hard limit on training steps. Set to -1 to use epochs instead.</span></span>
                                </label>
                                <input type="number" name="max_steps" value="-1" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Early Stop Patience
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Stop after N evals without improvement. Leave blank to disable.</span></span>
                                </label>
                                <input type="number" name="early_stopping_patience" value="" placeholder="e.g. 3" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Early Stop Metric
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Metric to monitor for early stopping.</span></span>
                                </label>
                                <select name="early_stopping_metric" id="early_stopping_metric_causal" class="form-select font-mono">
                                    <option value="eval_loss" selected>eval_loss</option>
                                    <option value="eval_accuracy">eval_accuracy</option>
                                    <option value="eval_f1">eval_f1</option>
                                    <option value="eval_perplexity">eval_perplexity</option>
                                </select>
                            </div>
                            <div class="form-group flex items-center gap-3 pt-6">
                                <input type="checkbox" name="early_stopping_greater_is_better" id="early_stopping_greater_is_better_causal" class="form-checkbox">
                                <label for="early_stopping_greater_is_better_causal" class="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-1">Greater is Better
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Check if higher metric values are better. True for accuracy, false for loss.</span></span>
                                </label>
                            </div>
                        </div>
                        <div class="flex flex-wrap gap-6 mt-4 pt-4 border-t border-gray-100 dark:border-gray-700">
                            <label class="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" name="gradient_checkpointing" checked class="form-checkbox">
                                <span class="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-1">Gradient Checkpointing
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Trade compute for memory by recomputing activations. Essential for large models on limited GPU memory.</span></span>
                                </span>
                            </label>
                            <label class="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" name="fp16" checked class="form-checkbox">
                                <span class="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-1">FP16
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">16-bit floating point training. Faster and uses less memory. Works on most NVIDIA GPUs.</span></span>
                                </span>
                            </label>
                            <label class="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" name="bf16" class="form-checkbox">
                                <span class="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-1">BF16
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">BFloat16 training. Better numerical stability than FP16. Requires Ampere+ GPU (RTX 30xx, A100).</span></span>
                                </span>
                            </label>
                            <label class="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" name="auto_evaluate" class="form-checkbox">
                                <span class="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-1">Auto Evaluate
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Run all available benchmarks after training completes. Evaluations run serially.</span></span>
                                </span>
                            </label>
                        </div>
                    </div>
                </div>
                
                <div class="flex justify-end gap-3">
                    <a href="/datasets" class="px-4 py-2 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-100 rounded-lg transition-all">Cancel</a>
                    <button type="submit" class="btn-success px-8">Start Training</button>
                </div>
            </form>
        </div>
        
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Auto-select greater is better based on metric
            const metricSelect = document.getElementById('early_stopping_metric_causal');
            const greaterCheckbox = document.getElementById('early_stopping_greater_is_better_causal');
            if (metricSelect && greaterCheckbox) {
                metricSelect.addEventListener('change', function() {
                    const greaterIsBetter = ['eval_accuracy', 'eval_f1'].includes(this.value);
                    greaterCheckbox.checked = greaterIsBetter;
                });
            }
            
        });
        
        function handleConfigSelect(select) {
            const configIdInput = document.getElementById('config-id-input');
            const formSection = document.getElementById('form-config-section');
            const formSections = formSection ? [formSection, ...formSection.parentElement.querySelectorAll('.section-card:not(:first-of-type)')] : [];
            
            if (select.value) {
                // Config selected - hide form sections and set config_id
                configIdInput.value = select.value;
                formSections.forEach(section => {
                    section.style.opacity = '0.5';
                    section.querySelectorAll('input, select, textarea').forEach(el => el.disabled = true);
                });
            } else {
                // No config selected - show form sections
                configIdInput.value = '';
                formSections.forEach(section => {
                    section.style.opacity = '1';
                    section.querySelectorAll('input, select, textarea').forEach(el => el.disabled = false);
                });
            }
        }
        </script>
        {% endblock %}""",
    )
)

COPY_EXPERIMENT_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Copy Experiment{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="max-w-4xl mx-auto">
            <div class="mb-6">
                <div class="flex items-center gap-3 mb-2">
                    <span class="badge badge-green">Causal LM</span>
                    <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Copy Experiment</h1>
                </div>
                <p class="text-gray-600 dark:text-gray-400">
                    Copying from: <span class="font-mono text-gray-500 dark:text-gray-400">{{ source_experiment.id[:16] }}...</span>
                    <span class="text-gray-400">•</span>
                    Dataset: <span class="font-medium text-gray-900 dark:text-gray-100">{{ dataset.filename }}</span>
                </p>
            </div>
            
            <form action="/experiments/causal-lm" method="post" class="space-y-6">
                <input type="hidden" name="dataset_id" value="{{ dataset.id }}">
                
                <!-- Data Config -->
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"></path></svg>
                        <h2 class="section-title">Data Configuration</h2>
                    </div>
                    <div class="section-body space-y-4">
                        <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Question Field
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">CSV column name containing the question/input text.</span></span>
                                </label>
                                <input type="text" name="question_field" value="{{ cfg.data.question_field }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Answer Field
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">CSV column name containing the answer/output text.</span></span>
                                </label>
                                <input type="text" name="answer_field" value="{{ cfg.data.answer_field }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Validation Split
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Fraction of data reserved for validation. Values: 0.05-0.5</span></span>
                                </label>
                                <input type="number" name="validation_split" value="{{ cfg.data.validation_split }}" step="0.05" min="0.05" max="0.5" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Random Seed
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Random seed for reproducible train/val splits. Use same seed to reproduce results.</span></span>
                                </label>
                                <input type="number" name="seed" value="{{ cfg.data.seed }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Max Length
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Max tokens per sample. Longer sequences are truncated. Higher = more memory.</span></span>
                                </label>
                                <input type="number" name="max_length" value="{{ cfg.data.max_length }}" class="form-input">
                            </div>
                        </div>
                        <div class="form-group">
                            <label class="form-label flex items-center gap-1">System Prompt
                                <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Instructions given to the model before each conversation. Sets the context and behavior.</span></span>
                            </label>
                            <textarea name="system_prompt" rows="2" class="form-textarea">{{ cfg.data.system_prompt }}</textarea>
                        </div>
                        <div class="form-group">
                            <label class="form-label flex items-center gap-1">Chat Template <span class="text-gray-400 font-normal">(use {system_prompt}, {question}, {answer})</span>
                                <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Template for formatting training samples. Use {system_prompt}, {question}, {answer} placeholders.</span></span>
                            </label>
                            <textarea name="template" rows="4" class="form-textarea text-xs">{{ cfg.data.template }}</textarea>
                        </div>
                    </div>
                </div>
                
                <!-- Model Config -->
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                        <h2 class="section-title">Model Configuration</h2>
                    </div>
                    <div class="section-body">
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div class="form-group md:col-span-2">
                                <label class="form-label flex items-center gap-1">Pretrained Model
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">HuggingFace model ID or local path. Examples: TinyLlama/TinyLlama-1.1B-Chat-v1.0</span></span>
                                </label>
                                <input type="text" name="pretrained_model_name" value="{{ cfg.model.pretrained_model_name }}" class="form-input font-mono text-sm">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Pad Token Override
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Override the padding token. Leave blank for model default. Some models need eos_token.</span></span>
                                </label>
                                <input type="text" name="pad_token_override" value="{{ cfg.model.pad_token_override or '' }}" class="form-input font-mono">
                            </div>
                            <div class="form-group flex items-center gap-3 pt-2">
                                <input type="checkbox" name="trust_remote_code" id="trust_remote_code_copy" class="form-checkbox" {% if cfg.model.trust_remote_code %}checked{% endif %}>
                                <label for="trust_remote_code_copy" class="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-1">Trust Remote Code
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Allow executing custom code from model repo. Required for some models. Security risk for untrusted sources.</span></span>
                                </label>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- PEFT Config -->
                {% if cfg.peft %}
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"></path></svg>
                        <h2 class="section-title">LoRA / PEFT Configuration</h2>
                    </div>
                    <div class="section-body">
                        <div class="flex items-center gap-3 mb-4 pb-4 border-b border-gray-100 dark:border-gray-700">
                            <input type="checkbox" name="peft_enabled" id="peft_enabled_copy" class="form-checkbox" {% if cfg.peft.enabled %}checked{% endif %}>
                            <label for="peft_enabled_copy" class="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-1">Enable LoRA Adapters
                                <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Use Low-Rank Adaptation instead of full fine-tuning. Much faster and uses less memory. Recommended for most cases.</span></span>
                            </label>
                        </div>
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Rank (r)
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">LoRA rank - dimensionality of adapter matrices. Higher = more trainable params. Common: 4, 8, 16, 32, 64</span></span>
                                </label>
                                <input type="number" name="peft_r" value="{{ cfg.peft.r }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Alpha
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">LoRA scaling factor. Controls adapter strength. Often set to 2x the rank value.</span></span>
                                </label>
                                <input type="number" name="peft_lora_alpha" value="{{ cfg.peft.lora_alpha }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Dropout
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Dropout probability for LoRA layers. Helps prevent overfitting. Range: 0.0-0.1</span></span>
                                </label>
                                <input type="number" name="peft_lora_dropout" value="{{ cfg.peft.lora_dropout }}" step="0.01" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Bias
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Which bias params to train. none: no biases, lora_only: only LoRA biases, all: all biases</span></span>
                                </label>
                                <select name="peft_bias" class="form-select">
                                    <option value="none" {% if cfg.peft.bias == 'none' %}selected{% endif %}>none</option>
                                    <option value="lora_only" {% if cfg.peft.bias == 'lora_only' %}selected{% endif %}>lora_only</option>
                                    <option value="all" {% if cfg.peft.bias == 'all' %}selected{% endif %}>all</option>
                                </select>
                            </div>
                            <div class="form-group md:col-span-4">
                                <label class="form-label flex items-center gap-1">Target Modules <span class="text-gray-400 font-normal">(comma-separated)</span>
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Model layers to apply LoRA. Common attention layers: q_proj, k_proj, v_proj, o_proj. Add gate_proj, up_proj, down_proj for MLP.</span></span>
                                </label>
                                <input type="text" name="peft_target_modules" value="{{ cfg.peft.target_modules | join(',') if cfg.peft.target_modules is iterable and cfg.peft.target_modules is not string else cfg.peft.target_modules }}" class="form-input font-mono text-sm">
                            </div>
                        </div>
                    </div>
                </div>
                {% endif %}
                
                <!-- Training Config -->
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                        <h2 class="section-title">Training Configuration</h2>
                    </div>
                    <div class="section-body">
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Epochs
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Number of complete passes through training data.</span></span>
                                </label>
                                <input type="number" name="num_train_epochs" value="{{ cfg.training.num_train_epochs }}" step="0.5" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Learning Rate
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Step size for optimizer. For LoRA: 1e-4 to 2e-4 typical. Full fine-tune: 1e-5 to 5e-5</span></span>
                                </label>
                                <input type="text" name="learning_rate" value="{{ cfg.training.learning_rate }}" class="form-input font-mono">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Train Batch Size
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Samples per device per step. Small for LLMs (1-4). Use gradient accumulation for larger effective batch.</span></span>
                                </label>
                                <input type="number" name="per_device_train_batch_size" value="{{ cfg.training.per_device_train_batch_size }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Eval Batch Size
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Samples per device during evaluation. Can be slightly larger than train batch.</span></span>
                                </label>
                                <input type="number" name="per_device_eval_batch_size" value="{{ cfg.training.per_device_eval_batch_size }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Weight Decay
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">L2 regularization factor. Often 0.0 for LoRA, 0.01-0.1 for full fine-tune.</span></span>
                                </label>
                                <input type="number" name="weight_decay" value="{{ cfg.training.weight_decay }}" step="0.01" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Warmup Ratio
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Fraction of training for LR warmup. Gradually increases LR from 0. Typical: 0.03-0.1</span></span>
                                </label>
                                <input type="number" name="warmup_ratio" value="{{ cfg.training.warmup_ratio }}" step="0.01" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Gradient Accum Steps
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Accumulate gradients over N steps. Effective batch = batch_size * accum_steps. Use to simulate larger batches on limited memory.</span></span>
                                </label>
                                <input type="number" name="gradient_accumulation_steps" value="{{ cfg.training.gradient_accumulation_steps }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">LR Scheduler
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Learning rate schedule. cosine: smooth decay, linear: steady decay, constant: no decay</span></span>
                                </label>
                                <select name="lr_scheduler_type" class="form-select">
                                    <option value="cosine" {% if cfg.training.lr_scheduler_type == 'cosine' %}selected{% endif %}>cosine</option>
                                    <option value="linear" {% if cfg.training.lr_scheduler_type == 'linear' %}selected{% endif %}>linear</option>
                                    <option value="constant" {% if cfg.training.lr_scheduler_type == 'constant' %}selected{% endif %}>constant</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Logging Steps
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Log training metrics every N steps.</span></span>
                                </label>
                                <input type="number" name="logging_steps" value="{{ cfg.training.logging_steps }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Eval Steps
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Run evaluation on validation set every N steps.</span></span>
                                </label>
                                <input type="number" name="eval_steps" value="{{ cfg.training.eval_steps }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Save Steps
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Save model checkpoint every N steps.</span></span>
                                </label>
                                <input type="number" name="save_steps" value="{{ cfg.training.save_steps }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Max Steps <span class="text-gray-400 font-normal">(-1 = off)</span>
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Hard limit on training steps. Set to -1 to use epochs instead.</span></span>
                                </label>
                                <input type="number" name="max_steps" value="{{ cfg.training.max_steps }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Early Stop Patience <span class="text-gray-400 font-normal">(blank = off)</span>
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Stop after N evals without improvement. Leave blank to disable.</span></span>
                                </label>
                                <input type="number" name="early_stopping_patience" value="{{ cfg.training.early_stopping_patience if cfg.training.early_stopping_patience else '' }}" placeholder="e.g. 3" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Early Stop Metric
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Metric to monitor for early stopping.</span></span>
                                </label>
                                <select name="early_stopping_metric" id="early_stopping_metric_copy" class="form-select font-mono">
                                    <option value="eval_loss" {% if not cfg.training.early_stopping_metric or cfg.training.early_stopping_metric == 'eval_loss' %}selected{% endif %}>eval_loss</option>
                                    <option value="eval_accuracy" {% if cfg.training.early_stopping_metric == 'eval_accuracy' %}selected{% endif %}>eval_accuracy</option>
                                    <option value="eval_f1" {% if cfg.training.early_stopping_metric == 'eval_f1' %}selected{% endif %}>eval_f1</option>
                                    <option value="eval_perplexity" {% if cfg.training.early_stopping_metric == 'eval_perplexity' %}selected{% endif %}>eval_perplexity</option>
                                </select>
                            </div>
                            <div class="form-group flex items-center gap-3 pt-6">
                                <input type="checkbox" name="early_stopping_greater_is_better" id="early_stopping_greater_is_better_copy" class="form-checkbox" {% if cfg.training.early_stopping_greater_is_better %}checked{% endif %}>
                                <label for="early_stopping_greater_is_better_copy" class="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-1">Greater is Better
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Check if higher metric values are better. True for accuracy, false for loss.</span></span>
                                </label>
                            </div>
                        </div>
                        <div class="flex flex-wrap gap-6 mt-4 pt-4 border-t border-gray-100 dark:border-gray-700">
                            <label class="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" name="gradient_checkpointing" class="form-checkbox" {% if cfg.training.gradient_checkpointing %}checked{% endif %}>
                                <span class="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-1">Gradient Checkpointing
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Trade compute for memory by recomputing activations. Essential for large models on limited GPU memory.</span></span>
                                </span>
                            </label>
                            <label class="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" name="fp16" class="form-checkbox" {% if cfg.training.fp16 %}checked{% endif %}>
                                <span class="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-1">FP16
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">16-bit floating point training. Faster and uses less memory. Works on most NVIDIA GPUs.</span></span>
                                </span>
                            </label>
                            <label class="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" name="bf16" class="form-checkbox" {% if cfg.training.bf16 %}checked{% endif %}>
                                <span class="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-1">BF16
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">BFloat16 training. Better numerical stability than FP16. Requires Ampere+ GPU (RTX 30xx, A100).</span></span>
                                </span>
                            </label>
                            <label class="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" name="auto_evaluate" class="form-checkbox" {% if cfg.training.auto_evaluate %}checked{% endif %}>
                                <span class="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-1">Auto Evaluate
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Run all available benchmarks after training completes. Evaluations run serially.</span></span>
                                </span>
                            </label>
                        </div>
                    </div>
                </div>
                
                <div class="flex justify-end gap-3">
                    <a href="/experiments/{{ source_experiment.id }}" class="px-4 py-2 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-100 rounded-lg transition-all">Cancel</a>
                    <button type="submit" class="btn-success px-8">Start Training</button>
                </div>
            </form>
        </div>
        
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Auto-select greater is better based on metric
            const metricSelect = document.getElementById('early_stopping_metric_copy');
            const greaterCheckbox = document.getElementById('early_stopping_greater_is_better_copy');
            if (metricSelect && greaterCheckbox) {
                metricSelect.addEventListener('change', function() {
                    const greaterIsBetter = ['eval_accuracy', 'eval_f1'].includes(this.value);
                    greaterCheckbox.checked = greaterIsBetter;
                });
            }
        });
        </script>
        {% endblock %}""",
    )
)

EXPERIMENTS_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Experiments - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="flex items-center justify-between mb-6">
            <div>
                <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Experiments</h1>
                <p class="text-gray-600 dark:text-gray-400">Track and manage your training runs</p>
            </div>
            <a href="/datasets" class="btn-primary">New Experiment</a>
        </div>
        
        <div class="card">
            <div class="overflow-x-auto">
                <table class="w-full" id="experiments-table">
                    <thead>
                        <tr class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100" data-sort="id">
                                ID <span class="sort-icon text-gray-400 ml-1">↕</span>
                            </th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100" data-sort="type">
                                Type <span class="sort-icon text-gray-400 ml-1">↕</span>
                            </th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100" data-sort="dataset">
                                Dataset <span class="sort-icon text-gray-400 ml-1">↕</span>
                            </th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100" data-sort="model">
                                Model <span class="sort-icon text-gray-400 ml-1">↕</span>
                            </th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100" data-sort="status">
                                Status <span class="sort-icon text-gray-400 ml-1">↕</span>
                            </th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100" data-sort="started">
                                Started <span class="sort-icon text-gray-400 ml-1">↕</span>
                            </th>
                            <th class="px-6 py-3 text-right text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Actions</th>
                        </tr>
                        <tr class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                            <td class="px-4 py-2"><input type="text" class="filter-input form-input text-xs py-1" data-col="0" placeholder="Filter..."></td>
                            <td class="px-4 py-2">
                                <select class="filter-select form-select text-xs py-1" data-col="1">
                                    <option value="">All</option>
                                    <option value="causal">Causal</option>
                                    <option value="mlm">MLM</option>
                                </select>
                            </td>
                            <td class="px-4 py-2"><input type="text" class="filter-input form-input text-xs py-1" data-col="2" placeholder="Filter..."></td>
                            <td class="px-4 py-2"><input type="text" class="filter-input form-input text-xs py-1" data-col="3" placeholder="Filter..."></td>
                            <td class="px-4 py-2">
                                <select class="filter-select form-select text-xs py-1" data-col="4">
                                    <option value="">All</option>
                                    <option value="completed">Completed</option>
                                    <option value="running">Running</option>
                                    <option value="failed">Failed</option>
                                    <option value="pending">Pending</option>
                                </select>
                            </td>
                            <td class="px-4 py-2"><input type="text" class="filter-input form-input text-xs py-1" data-col="5" placeholder="Filter..."></td>
                            <td class="px-4 py-2"></td>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100" id="experiments-tbody">
                        {% for exp in experiments %}
                        <tr class="hover:bg-gray-50 dark:hover:bg-gray-700 dark:bg-gray-800 transition-colors exp-row" 
                            data-id="{{ exp.id[:8] }}" 
                            data-type="{{ exp.experiment_type }}" 
                            data-dataset="{{ exp.dataset_filename or 'N/A' }}" 
                            data-model="{{ exp.config.model.pretrained_model_name }}" 
                            data-status="{{ exp.status }}" 
                            data-started="{{ exp.started_at }}">
                            <td class="px-6 py-4 font-mono text-sm text-gray-600 dark:text-gray-400">{{ exp.id[:8] }}</td>
                            <td class="px-6 py-4">
                                {% if exp.experiment_type == 'causal_lm' %}
                                <span class="badge badge-green">Causal</span>
                                {% else %}
                                <span class="badge badge-blue">MLM</span>
                                {% endif %}
                            </td>
                            <td class="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{{ exp.dataset_filename or 'N/A' }}</td>
                            <td class="px-6 py-4 text-sm text-gray-600 dark:text-gray-400 font-mono">{{ exp.config.model.pretrained_model_name | truncate(20) }}</td>
                            <td class="px-6 py-4">
                                {% if exp.status == 'completed' %}
                                <span class="badge badge-green">Completed</span>
                                {% elif exp.status == 'running' %}
                                <span class="badge badge-blue">Running</span>
                                {% elif exp.status == 'failed' %}
                                <span class="badge badge-red">Failed</span>
                                {% elif exp.status == 'stopped' %}
                                <span class="badge badge-amber">Stopped</span>
                                {% else %}
                                <span class="badge badge-gray">Pending</span>
                                {% endif %}
                            </td>
                            <td class="px-6 py-4 text-sm text-gray-500 dark:text-gray-400"><span data-utc="{{ exp.started_at }}">{{ exp.started_at[:16] }}</span></td>
                            <td class="px-6 py-4">
                                <div class="flex items-center justify-end gap-3">
                                    <a href="/experiments/{{ exp.id }}" class="text-sm font-medium text-primary-600 hover:text-primary-800">View</a>
                                    <form action="/experiments/{{ exp.id }}/delete" method="post" class="inline" onsubmit="return confirm('Delete this experiment and its artifacts?')">
                                        <button type="submit" class="text-sm font-medium text-red-500 hover:text-red-700">Delete</button>
                                    </form>
                                </div>
                            </td>
                        </tr>
                        {% else %}
                        <tr id="no-experiments-row">
                            <td colspan="7" class="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
                                <div class="flex flex-col items-center">
                                    <svg class="w-12 h-12 text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path></svg>
                                    <p>No experiments yet. Upload a dataset to get started!</p>
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        
        <script>
        (function() {
            const table = document.getElementById('experiments-table');
            const tbody = document.getElementById('experiments-tbody');
            const rows = Array.from(tbody.querySelectorAll('.exp-row'));
            
            if (rows.length === 0) return;
            
            let sortCol = null;
            let sortAsc = true;
            
            // Sorting
            table.querySelectorAll('th[data-sort]').forEach(th => {
                th.addEventListener('click', () => {
                    const col = th.dataset.sort;
                    if (sortCol === col) {
                        sortAsc = !sortAsc;
                    } else {
                        sortCol = col;
                        sortAsc = true;
                    }
                    
                    // Update icons
                    table.querySelectorAll('.sort-icon').forEach(icon => icon.textContent = '↕');
                    th.querySelector('.sort-icon').textContent = sortAsc ? '↑' : '↓';
                    
                    const colMap = {id: 'id', type: 'type', dataset: 'dataset', model: 'model', status: 'status', started: 'started'};
                    const dataAttr = 'data-' + colMap[col];
                    
                    rows.sort((a, b) => {
                        const aVal = a.getAttribute(dataAttr).toLowerCase();
                        const bVal = b.getAttribute(dataAttr).toLowerCase();
                        if (aVal < bVal) return sortAsc ? -1 : 1;
                        if (aVal > bVal) return sortAsc ? 1 : -1;
                        return 0;
                    });
                    
                    rows.forEach(row => tbody.appendChild(row));
                    applyFilters();
                });
            });
            
            // Filtering
            function applyFilters() {
                const filters = {};
                table.querySelectorAll('.filter-input').forEach(input => {
                    filters[input.dataset.col] = input.value.toLowerCase();
                });
                table.querySelectorAll('.filter-select').forEach(select => {
                    filters[select.dataset.col] = select.value.toLowerCase();
                });
                
                rows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    let show = true;
                    
                    Object.entries(filters).forEach(([col, val]) => {
                        if (!val) return;
                        const cellText = cells[parseInt(col)].textContent.toLowerCase();
                        if (!cellText.includes(val)) show = false;
                    });
                    
                    row.style.display = show ? '' : 'none';
                });
            }
            
            table.querySelectorAll('.filter-input').forEach(input => {
                input.addEventListener('input', applyFilters);
            });
            table.querySelectorAll('.filter-select').forEach(select => {
                select.addEventListener('change', applyFilters);
            });
        })();
        </script>
        {% endblock %}""",
    )
)

EXPERIMENT_DETAIL_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Experiment Details - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="mb-6">
            <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-3">
                    {% if experiment.experiment_type == 'causal_lm' %}
                    <span class="badge badge-green">Causal LM</span>
                    {% else %}
                    <span class="badge badge-blue">Masked LM</span>
                    {% endif %}
                    <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Experiment Details</h1>
                </div>
                <a href="/experiments" class="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white">&larr; Back to Experiments</a>
            </div>
            <div class="flex items-center justify-end gap-3">
                {% if experiment.status == 'running' %}
                <button type="button" id="stop-btn" onclick="stopExperiment()" class="bg-amber-500 text-white px-4 py-2 rounded-lg font-medium hover:bg-amber-600 transition-all duration-200 shadow-sm hover:shadow-md flex items-center gap-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"></path></svg>
                    Stop Training
                </button>
                {% endif %}
                {% if experiment.status == 'completed' %}
                <button type="button" id="evaluate-btn" onclick="openEvaluateModal()" class="bg-amber-500 text-white px-4 py-2 rounded-lg font-medium hover:bg-amber-600 transition-all duration-200 shadow-sm hover:shadow-md flex items-center gap-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
                    Evaluate
                </button>
                <form action="/experiments/{{ experiment.id }}/extract-meta" method="post" class="inline" id="extract-meta-form">
                    <button type="submit" id="extract-meta-btn" class="bg-purple-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-purple-700 transition-all duration-200 shadow-sm hover:shadow-md flex items-center gap-2">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
                        Extract for Meta
                    </button>
                </form>
                {% endif %}
                <a href="/experiments/{{ experiment.id }}/copy" class="btn-primary flex items-center gap-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                    Copy & Edit
                </a>
                <form action="/experiments/{{ experiment.id }}/delete" method="post" class="inline" onsubmit="return confirm('Delete this experiment and its artifacts?')">
                    <button type="submit" class="btn-danger flex items-center gap-2">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                        Delete
                    </button>
                </form>
            </div>
        </div>
        
        <!-- Status Card -->
        <div class="card mb-6">
            <div class="card-body">
                <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
                    <div>
                        <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">Experiment ID</p>
                        <p class="font-mono text-sm text-gray-900 dark:text-gray-100">{{ experiment.id[:16] }}...</p>
                    </div>
                    <div>
                        <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">Status</p>
                        {% if experiment.status == 'completed' %}
                        <span class="badge badge-green">Completed</span>
                        {% elif experiment.status == 'running' %}
                        <span class="badge badge-blue">Running</span>
                        {% elif experiment.status == 'evaluating' %}
                        <span class="badge badge-purple">Evaluating</span>
                        {% elif experiment.status == 'failed' %}
                        <span class="badge badge-red">Failed</span>
                        {% elif experiment.status == 'stopped' %}
                        <span class="badge badge-amber">Stopped</span>
                        {% else %}
                        <span class="badge badge-gray">Pending</span>
                        {% endif %}
                    </div>
                    <div>
                        <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">Dataset</p>
                        <p class="text-sm text-gray-900 dark:text-gray-100">{{ experiment.dataset_filename or 'N/A' }}</p>
                    </div>
                    <div>
                        <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">Model</p>
                        <p class="font-mono text-sm text-gray-900 dark:text-gray-100">{{ experiment.config.model.pretrained_model_name | truncate(25) }}</p>
                    </div>
                    <div>
                        <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">Started</p>
                        <p class="text-sm text-gray-900 dark:text-gray-100"><span data-utc="{{ experiment.started_at }}">{{ experiment.started_at[:19] }}</span></p>
                    </div>
                    <div>
                        <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">Completed</p>
                        <p class="text-sm text-gray-900 dark:text-gray-100">{% if experiment.completed_at %}<span data-utc="{{ experiment.completed_at }}">{{ experiment.completed_at[:19] }}</span>{% else %}In progress...{% endif %}</p>
                    </div>
                    {% if experiment.output_dir %}
                    <div class="col-span-2">
                        <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">Output Directory</p>
                        <p class="font-mono text-sm text-gray-900 dark:text-gray-100">{{ experiment.output_dir }}</p>
                    </div>
                    {% endif %}
                </div>
                {% if experiment.error %}
                <div class="mt-4 p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg">
                    <p class="text-sm font-medium text-red-800">Error</p>
                    <p class="text-sm text-red-700 mt-1">{{ experiment.error }}</p>
                </div>
                {% endif %}
                
            </div>
        </div>
        
        {% if experiment.status == 'running' or experiment.status == 'pending' %}
        <!-- Sticky Progress Bar -->
        <div class="sticky top-16 z-40 -mx-4 px-4 py-3 bg-white/95 dark:bg-gray-900/95 backdrop-blur-sm border-b border-gray-200 dark:border-gray-700 shadow-sm">
            <div class="flex items-center gap-4">
                <div class="flex-1">
                    <div class="flex items-center justify-between mb-1">
                        <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Training Progress</p>
                        <div class="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                            <span id="progress-step">Step: --</span>
                            <span id="progress-epoch">Epoch: -- / {{ experiment.config.training.num_train_epochs }}</span>
                        </div>
                    </div>
                    <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 overflow-hidden">
                        <div id="progress-bar" class="progress-bar-animated h-2.5 rounded-full transition-all duration-500 ease-out" style="width: 0%"></div>
                    </div>
                </div>
                <p id="progress-text" class="text-lg font-semibold text-blue-600 dark:text-blue-400 min-w-[4rem] text-right">0%</p>
            </div>
        </div>
        <style>
            .progress-bar-animated {
                background: linear-gradient(
                    90deg,
                    #3b82f6 0%,
                    #60a5fa 25%,
                    #93c5fd 50%,
                    #60a5fa 75%,
                    #3b82f6 100%
                );
                background-size: 200% 100%;
                animation: shimmer 2s ease-in-out infinite;
            }
            @keyframes shimmer {
                0% { background-position: 200% 0; }
                100% { background-position: -200% 0; }
            }
        </style>
        {% endif %}
        
        <!-- Metrics -->
        {% if experiment.metrics %}
        <div class="card mb-6">
            <div class="card-header">
                <h2 class="font-semibold text-gray-800 dark:text-gray-200">Training Metrics</h2>
            </div>
            <div class="card-body">
                <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
                    {% for key, value in experiment.metrics.items() %}
                    <div class="metric-card">
                        <p class="metric-label mb-1">{{ key.replace('_', ' ') }}</p>
                        <p class="metric-value">
                            {% if value is number %}
                                {% if value > 1000000 %}{{ "%.2e"|format(value) }}{% elif value > 100 %}{{ "%.1f"|format(value) }}{% else %}{{ "%.4f"|format(value) }}{% endif %}
                            {% else %}{{ value }}{% endif %}
                        </p>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
        {% endif %}
        
        <!-- Configuration -->
        <div class="card">
            <div class="card-header">
                <h2 class="font-semibold text-gray-800 dark:text-gray-200">Configuration</h2>
            </div>
            <div class="card-body space-y-6">
                <!-- Data Config -->
                <div>
                    <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide mb-3 flex items-center gap-2">
                        <svg class="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"></path></svg>
                        Data
                    </h3>
                    <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                            {% for key, value in experiment.config.data.items() %}
                            <div>
                                <span class="text-gray-500 dark:text-gray-400">{{ key }}:</span>
                                <span class="text-gray-900 dark:text-gray-100 ml-1 font-medium">{{ value if value is not none else 'N/A' }}</span>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
                
                <!-- Model Config -->
                <div>
                    <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide mb-3 flex items-center gap-2">
                        <svg class="w-4 h-4 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                        Model
                    </h3>
                    <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                            {% for key, value in experiment.config.model.items() %}
                            <div>
                                <span class="text-gray-500 dark:text-gray-400">{{ key }}:</span>
                                <span class="text-gray-900 dark:text-gray-100 ml-1 font-medium">{{ value if value is not none else 'N/A' }}</span>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
                
                <!-- Training Config -->
                <div>
                    <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide mb-3 flex items-center gap-2">
                        <svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                        Training
                    </h3>
                    <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                            {% for key, value in experiment.config.training.items() %}
                            <div>
                                <span class="text-gray-500 dark:text-gray-400">{{ key }}:</span>
                                <span class="text-gray-900 dark:text-gray-100 ml-1 font-medium">{{ value if value is not none else 'N/A' }}</span>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
                
                <!-- PEFT Config -->
                {% if experiment.config.peft %}
                <div>
                    <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide mb-3 flex items-center gap-2">
                        <svg class="w-4 h-4 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"></path></svg>
                        PEFT / LoRA
                    </h3>
                    <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                            {% for key, value in experiment.config.peft.items() %}
                            <div>
                                <span class="text-gray-500 dark:text-gray-400">{{ key }}:</span>
                                <span class="text-gray-900 dark:text-gray-100 ml-1 font-medium">{{ value if value is not none else 'N/A' }}</span>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
                {% endif %}
            </div>
        </div>
        
        <!-- Learning Curve Chart -->
        {% if logs %}
        <div class="card mt-6">
            <div class="card-header">
                <h2 class="font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
                    <svg class="w-5 h-5 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z"></path></svg>
                    Learning Curve
                </h2>
            </div>
            <div class="card-body">
                <div id="learning-curve-chart" style="width:100%; height:400px;"></div>
            </div>
        </div>
        <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
        <script>
            (function() {
                const logs = {{ logs | tojson }};
                const trainLoss = [];
                const evalLoss = [];
                
                logs.forEach(entry => {
                    if (entry.step !== undefined) {
                        if (entry.loss !== undefined) {
                            trainLoss.push({x: entry.step, y: entry.loss});
                        }
                        if (entry.eval_loss !== undefined) {
                            evalLoss.push({x: entry.step, y: entry.eval_loss});
                        }
                    }
                });
                
                const traces = [];
                if (trainLoss.length > 0) {
                    traces.push({
                        x: trainLoss.map(p => p.x),
                        y: trainLoss.map(p => p.y),
                        mode: 'lines+markers',
                        name: 'Train Loss',
                        line: {color: '#3b82f6'},
                        marker: {size: 6}
                    });
                }
                if (evalLoss.length > 0) {
                    traces.push({
                        x: evalLoss.map(p => p.x),
                        y: evalLoss.map(p => p.y),
                        mode: 'lines+markers',
                        name: 'Eval Loss',
                        line: {color: '#10b981'},
                        marker: {size: 6}
                    });
                }
                
                const layout = {
                    title: '{{ experiment.config.model.pretrained_model_name }} Loss Curve',
                    xaxis: {title: 'Global Step'},
                    yaxis: {title: 'Loss'},
                    template: 'plotly_white',
                    legend: {orientation: 'h', y: -0.15},
                    margin: {t: 50, b: 80}
                };
                
                if (traces.length > 0) {
                    Plotly.newPlot('learning-curve-chart', traces, layout, {responsive: true});
                } else {
                    document.getElementById('learning-curve-chart').innerHTML = '<p class="text-center text-gray-500 dark:text-gray-400 py-8">No loss data available yet</p>';
                }
            })();
        </script>
        {% endif %}
        
        <!-- Training Logs -->
        <div class="card mt-6">
            <div class="card-header flex items-center justify-between">
                <h2 class="font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
                    <svg class="w-5 h-5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                    Training Logs
                    {% if experiment.status == 'running' or experiment.status == 'pending' %}
                    <span id="logs-status" class="ml-2 text-xs font-medium text-blue-600">(live)</span>
                    {% endif %}
                </h2>
                <span id="logs-count" class="text-sm text-gray-500 dark:text-gray-400">{{ logs|length }} entries</span>
            </div>
            <div class="card-body">
                <div class="overflow-x-auto">
                    <table class="w-full text-sm">
                        <thead>
                            <tr class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                                <th class="px-4 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">Step</th>
                                <th class="px-4 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">Epoch</th>
                                <th class="px-4 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">Loss</th>
                                <th class="px-4 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">Eval Loss</th>
                                <th class="px-4 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">Learning Rate</th>
                                <th class="px-4 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">Grad Norm</th>
                            </tr>
                        </thead>
                        <tbody id="logs-table-body" class="divide-y divide-gray-100">
                            {% for entry in logs %}
                            <tr class="hover:bg-gray-50 dark:hover:bg-gray-700 dark:hover:bg-gray-700 dark:bg-gray-800/50">
                                <td class="px-4 py-2 font-mono text-gray-900 dark:text-gray-100">{{ entry.step if entry.step is defined else '-' }}</td>
                                <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ "%.2f"|format(entry.epoch) if entry.epoch is defined else '-' }}</td>
                                <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ "%.4f"|format(entry.loss) if entry.loss is defined else '-' }}</td>
                                <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ "%.4f"|format(entry.eval_loss) if entry.eval_loss is defined else '-' }}</td>
                                <td class="px-4 py-2 font-mono text-gray-600 dark:text-gray-400 text-xs">{{ "%.2e"|format(entry.learning_rate) if entry.learning_rate is defined else '-' }}</td>
                                <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ "%.2f"|format(entry.grad_norm) if entry.grad_norm is defined else '-' }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% if not logs %}
                <p id="no-logs-msg" class="text-center text-gray-500 dark:text-gray-400 py-4">No logs available yet</p>
                {% endif %}
            </div>
        </div>
        
        {% if experiment.status == 'running' or experiment.status == 'pending' %}
        <script>
            const experimentId = "{{ experiment.id }}";
            const totalEpochs = {{ experiment.config.training.num_train_epochs }};
            const maxSteps = {{ experiment.config.training.max_steps }};
            let lastLogCount = {{ logs|length }};
            
            function formatNumber(val, decimals) {
                if (val === undefined || val === null) return '-';
                return Number(val).toFixed(decimals);
            }
            
            function formatScientific(val) {
                if (val === undefined || val === null) return '-';
                return Number(val).toExponential(2);
            }
            
            function updateProgress(logs) {
                if (logs.length === 0) return;
                
                // Find latest entry with epoch/step info
                let latestEpoch = null;
                let latestStep = null;
                for (let i = logs.length - 1; i >= 0; i--) {
                    if (latestEpoch === null && logs[i].epoch !== undefined) {
                        latestEpoch = logs[i].epoch;
                    }
                    if (latestStep === null && logs[i].step !== undefined) {
                        latestStep = logs[i].step;
                    }
                    if (latestEpoch !== null && latestStep !== null) break;
                }
                
                if (latestEpoch === null) return;
                
                // Calculate progress percentage
                let progress;
                if (maxSteps > 0 && latestStep !== null) {
                    progress = (latestStep / maxSteps) * 100;
                } else {
                    progress = (latestEpoch / totalEpochs) * 100;
                }
                progress = Math.min(progress, 100);
                
                // Update progress bar
                document.getElementById('progress-bar').style.width = `${progress}%`;
                document.getElementById('progress-text').textContent = `${progress.toFixed(1)}%`;
                document.getElementById('progress-step').textContent = `Step: ${latestStep !== null ? latestStep : '--'}`;
                document.getElementById('progress-epoch').textContent = `Epoch: ${formatNumber(latestEpoch, 2)} / ${totalEpochs}`;
            }
            
            async function pollLogs() {
                try {
                    const resp = await fetch(`/api/experiments/${experimentId}/logs`);
                    const data = await resp.json();
                    const logs = data.logs || [];
                    
                    // Always update progress
                    updateProgress(logs);
                    
                    if (logs.length !== lastLogCount) {
                        lastLogCount = logs.length;
                        document.getElementById('logs-count').textContent = `${logs.length} entries`;
                        
                        const noLogsMsg = document.getElementById('no-logs-msg');
                        if (noLogsMsg && logs.length > 0) {
                            noLogsMsg.remove();
                        }
                        
                        const tbody = document.getElementById('logs-table-body');
                        tbody.innerHTML = logs.map(entry => `
                            <tr class="hover:bg-gray-50 dark:hover:bg-gray-700 dark:bg-gray-800">
                                <td class="px-4 py-2 font-mono text-gray-900 dark:text-gray-100">${entry.step !== undefined ? entry.step : '-'}</td>
                                <td class="px-4 py-2 text-gray-700 dark:text-gray-300">${formatNumber(entry.epoch, 2)}</td>
                                <td class="px-4 py-2 text-gray-700 dark:text-gray-300">${formatNumber(entry.loss, 4)}</td>
                                <td class="px-4 py-2 text-gray-700 dark:text-gray-300">${formatNumber(entry.eval_loss, 4)}</td>
                                <td class="px-4 py-2 font-mono text-gray-600 dark:text-gray-400 text-xs">${formatScientific(entry.learning_rate)}</td>
                                <td class="px-4 py-2 text-gray-700 dark:text-gray-300">${formatNumber(entry.grad_norm, 2)}</td>
                            </tr>
                        `).join('');
                    }
                    
                    // Check if experiment is still running
                    const expResp = await fetch(`/api/experiments/${experimentId}`);
                    const expData = await expResp.json();
                    if (expData.status === 'running' || expData.status === 'pending') {
                        setTimeout(pollLogs, 3000);
                    } else {
                        const statusEl = document.getElementById('logs-status');
                        if (statusEl) statusEl.remove();
                        // Reload page to get final state
                        location.reload();
                    }
                } catch (e) {
                    console.error('Error polling logs:', e);
                    setTimeout(pollLogs, 5000);
                }
            }
            
            // Initialize progress from existing logs
            updateProgress({{ logs | tojson }});
            setTimeout(pollLogs, 3000);
        </script>
        {% endif %}
        
        <!-- Stop Training Modal -->
        {% if experiment.status == 'running' %}
        <div id="stop-modal" class="fixed inset-0 bg-gray-900/50 backdrop-blur-sm hidden items-center justify-center z-50">
            <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl p-8 max-w-md mx-4 text-center">
                <div class="w-16 h-16 mx-auto mb-4">
                    <svg class="animate-spin w-16 h-16 text-amber-500" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                </div>
                <h3 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2">Stopping Training</h3>
                <p class="text-gray-600 dark:text-gray-400 mb-4">Waiting for the current training step to complete...</p>
                <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mb-4 overflow-hidden">
                    <div class="bg-amber-500 h-2 rounded-full animate-pulse" style="width: 100%"></div>
                </div>
                <div class="text-sm text-gray-500 dark:text-gray-400">
                    <p>The experiment will stop after the current step.</p>
                    <p>This may take a few moments.</p>
                </div>
            </div>
        </div>
        <script>
        async function stopExperiment() {
            const experimentId = "{{ experiment.id }}";
            const modal = document.getElementById('stop-modal');
            const stopBtn = document.getElementById('stop-btn');
            
            if (!confirm('Stop this training experiment?')) return;
            
            modal.classList.remove('hidden');
            modal.classList.add('flex');
            stopBtn.disabled = true;
            stopBtn.innerHTML = '<svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg> Stopping...';
            
            try {
                await fetch(`/experiments/${experimentId}/stop`, { method: 'POST' });
                
                async function pollStatus() {
                    const resp = await fetch(`/api/experiments/${experimentId}`);
                    const data = await resp.json();
                    if (data.status !== 'running' && data.status !== 'pending') {
                        location.reload();
                    } else {
                        setTimeout(pollStatus, 1000);
                    }
                }
                pollStatus();
            } catch (e) {
                console.error('Error stopping experiment:', e);
                modal.classList.add('hidden');
                modal.classList.remove('flex');
                stopBtn.disabled = false;
                stopBtn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"></path></svg> Stop Training';
                alert('Failed to stop experiment');
            }
        }
        </script>
        {% endif %}
        
        <!-- Extract Meta Modal -->
        {% if experiment.status == 'completed' %}
        <div id="extract-modal" class="fixed inset-0 bg-gray-900/50 backdrop-blur-sm hidden items-center justify-center z-50">
            <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl p-8 max-w-md mx-4 text-center">
                <div class="w-16 h-16 mx-auto mb-4">
                    <svg class="animate-spin w-16 h-16 text-purple-600" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                </div>
                <h3 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2">Extracting Meta-Features</h3>
                <p class="text-gray-600 dark:text-gray-400 mb-4">Running full evaluation to calculate ROUGE score...</p>
                <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mb-4 overflow-hidden">
                    <div class="bg-purple-600 h-2 rounded-full animate-pulse" style="width: 100%"></div>
                </div>
                <div class="text-sm text-gray-500 dark:text-gray-400">
                    <p>This may take up to 20 minutes depending on</p>
                    <p>model size and dataset length.</p>
                </div>
            </div>
        </div>
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            const form = document.getElementById('extract-meta-form');
            const modal = document.getElementById('extract-modal');
            const submitBtn = document.getElementById('extract-meta-btn');
            
            if (form && modal) {
                form.addEventListener('submit', function() {
                    modal.classList.remove('hidden');
                    modal.classList.add('flex');
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg> Extracting...';
                });
            }
        });
        </script>
        
        <!-- Evaluate Modal -->
        <div id="evaluate-modal" class="fixed inset-0 bg-gray-900/50 backdrop-blur-sm hidden items-center justify-center z-50">
            <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl p-6 max-w-lg mx-4 w-full">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-xl font-bold text-gray-900 dark:text-gray-100">Evaluate Experiment</h3>
                    <button onclick="closeEvaluateModal()" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                    </button>
                </div>
                
                <div id="evaluate-form-section">
                    {% if benchmarks %}
                    <form id="evaluate-form" class="space-y-4">
                        <div class="form-group">
                            <label class="form-label">Select Benchmark</label>
                            <select name="benchmark_id" id="benchmark-select" required class="form-select">
                                <option value="">Choose a benchmark...</option>
                                {% for benchmark in benchmarks %}
                                <option value="{{ benchmark.id }}">{{ benchmark.name }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="grid grid-cols-3 gap-4">
                            <div class="form-group">
                                <label class="form-label">Max Tokens</label>
                                <input type="number" name="max_new_tokens" value="128" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Temperature</label>
                                <input type="number" name="temperature" value="0.7" step="0.1" min="0" max="2" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Top P</label>
                                <input type="number" name="top_p" value="0.9" step="0.05" min="0" max="1" class="form-input">
                            </div>
                        </div>
                        <div class="flex justify-end gap-3 pt-2">
                            <button type="button" onclick="closeEvaluateModal()" class="px-4 py-2 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-all">Cancel</button>
                            <button type="submit" id="run-eval-btn" class="btn-success px-6">Run Evaluation</button>
                        </div>
                    </form>
                    {% else %}
                    <div class="text-center py-6">
                        <p class="text-gray-600 dark:text-gray-400 mb-4">No benchmarks available. Create a benchmark first.</p>
                        <a href="/benchmarks" class="btn-primary">Go to Benchmarks</a>
                    </div>
                    {% endif %}
                </div>
                
                <div id="evaluate-progress-section" class="hidden text-center py-4">
                    <div class="w-16 h-16 mx-auto mb-4">
                        <svg class="animate-spin w-16 h-16 text-amber-500" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                    </div>
                    <h3 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2">Running Evaluation</h3>
                    <p class="text-gray-600 dark:text-gray-400 mb-4">Generating model response and calculating ROUGE score...</p>
                    <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                        <div class="bg-amber-500 h-2 rounded-full animate-pulse" style="width: 100%"></div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
        function openEvaluateModal() {
            const modal = document.getElementById('evaluate-modal');
            modal.classList.remove('hidden');
            modal.classList.add('flex');
        }
        
        function closeEvaluateModal() {
            const modal = document.getElementById('evaluate-modal');
            modal.classList.add('hidden');
            modal.classList.remove('flex');
            // Reset to form view
            document.getElementById('evaluate-form-section').classList.remove('hidden');
            document.getElementById('evaluate-progress-section').classList.add('hidden');
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            const evalForm = document.getElementById('evaluate-form');
            if (evalForm) {
                evalForm.addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    const benchmarkId = document.getElementById('benchmark-select').value;
                    if (!benchmarkId) return;
                    
                    const formData = new FormData(evalForm);
                    const payload = {
                        experiment_id: "{{ experiment.id }}",
                        max_new_tokens: parseInt(formData.get('max_new_tokens')),
                        temperature: parseFloat(formData.get('temperature')),
                        top_p: parseFloat(formData.get('top_p'))
                    };
                    
                    // Show progress
                    document.getElementById('evaluate-form-section').classList.add('hidden');
                    document.getElementById('evaluate-progress-section').classList.remove('hidden');
                    
                    try {
                        const resp = await fetch(`/benchmarks/${benchmarkId}/evaluate`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/x-www-form-urlencoded',
                                'X-Requested-With': 'XMLHttpRequest'
                            },
                            body: new URLSearchParams(payload)
                        });
                        const data = await resp.json();
                        const evalId = data.eval_id;
                        
                        // Poll for completion
                        async function pollStatus() {
                            const statusResp = await fetch('/api/evaluations/' + evalId);
                            const statusData = await statusResp.json();
                            if (statusData.status === 'completed' || statusData.status === 'failed') {
                                window.location.href = '/benchmarks/' + benchmarkId + '/results';
                            } else {
                                setTimeout(pollStatus, 1000);
                            }
                        }
                        pollStatus();
                    } catch (err) {
                        console.error('Evaluation error:', err);
                        alert('Failed to start evaluation');
                        closeEvaluateModal();
                    }
                });
            }
        });
        </script>
        {% endif %}
        
        <!-- Auto-Evaluation Progress Modal -->
        {% if experiment.status == 'evaluating' %}
        <div id="auto-eval-modal" class="fixed inset-0 bg-gray-900/50 backdrop-blur-sm flex items-center justify-center z-50">
            <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl p-8 max-w-md mx-4 w-full">
                <div class="text-center">
                    <div class="w-20 h-20 mx-auto mb-6 relative">
                        <svg class="animate-spin w-20 h-20 text-purple-500" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <div class="absolute inset-0 flex items-center justify-center">
                            <span id="auto-eval-icon" class="text-2xl">📊</span>
                        </div>
                    </div>
                    <h3 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2">Running Benchmarks</h3>
                    <p id="auto-eval-current" class="text-gray-600 dark:text-gray-400 mb-4">
                        {% if experiment.auto_eval_current %}
                        Evaluating: {{ experiment.auto_eval_current }}
                        {% else %}
                        Starting evaluations...
                        {% endif %}
                    </p>
                    
                    <!-- Progress bar -->
                    <div class="mb-4">
                        <div class="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400 mb-2">
                            <span>Progress</span>
                            <span id="auto-eval-count">{{ experiment.auto_eval_completed }} / {{ experiment.auto_eval_total }}</span>
                        </div>
                        <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
                            <div id="auto-eval-progress" class="bg-purple-500 h-3 rounded-full transition-all duration-500" 
                                 style="width: {% if experiment.auto_eval_total > 0 %}{{ (experiment.auto_eval_completed / experiment.auto_eval_total * 100) | int }}{% else %}0{% endif %}%"></div>
                        </div>
                    </div>
                    
                    <p class="text-xs text-gray-400 dark:text-gray-500">
                        Auto-evaluate is running all benchmarks serially. This page will refresh when complete.
                    </p>
                </div>
            </div>
        </div>
        
        <script>
        // Poll for auto-evaluation status updates
        (function() {
            const experimentId = "{{ experiment.id }}";
            
            async function pollAutoEvalStatus() {
                try {
                    const resp = await fetch('/api/experiments/' + experimentId);
                    const data = await resp.json();
                    
                    if (data.status === 'completed' || data.status === 'failed') {
                        // Reload page to show final state
                        window.location.reload();
                        return;
                    }
                    
                    if (data.status === 'evaluating') {
                        // Update progress
                        const total = data.auto_eval_total || 1;
                        const completed = data.auto_eval_completed || 0;
                        const current = data.auto_eval_current || 'Processing...';
                        const percent = Math.round((completed / total) * 100);
                        
                        document.getElementById('auto-eval-current').textContent = 'Evaluating: ' + current;
                        document.getElementById('auto-eval-count').textContent = completed + ' / ' + total;
                        document.getElementById('auto-eval-progress').style.width = percent + '%';
                    }
                    
                    // Poll again
                    setTimeout(pollAutoEvalStatus, 2000);
                } catch (err) {
                    console.error('Poll error:', err);
                    setTimeout(pollAutoEvalStatus, 5000);
                }
            }
            
            // Start polling
            pollAutoEvalStatus();
        })();
        </script>
        {% endif %}
        {% endblock %}""",
    )
)


BENCHMARKS_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Benchmarks - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="mb-6">
            <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Benchmarks</h1>
            <p class="text-gray-600 dark:text-gray-400">Create question/answer pairs to evaluate experiments with ROUGE scores</p>
        </div>
        
        <div class="card mb-6">
            <div class="card-header">
                <h2 class="font-semibold text-gray-800 dark:text-gray-200">Create New Benchmark</h2>
            </div>
            <div class="card-body">
                <form action="/benchmarks/create" method="post" class="space-y-4">
                    <div class="form-group">
                        <label class="form-label">Benchmark Name</label>
                        <input type="text" name="name" placeholder="e.g. violence_q1" required class="form-input max-w-md">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Question</label>
                        <textarea name="question" rows="2" required class="form-textarea" placeholder="Enter the question to ask the model..."></textarea>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Gold Answer <span class="text-gray-400 font-normal">(expected answer)</span></label>
                        <textarea name="gold_answer" rows="3" required class="form-textarea" placeholder="Enter the expected/gold standard answer..."></textarea>
                    </div>
                    <div class="flex justify-end">
                        <button type="submit" class="btn-primary">Create Benchmark</button>
                    </div>
                </form>
            </div>
        </div>
        
        <div class="card">
            <div class="overflow-x-auto">
                <table class="w-full">
                    <thead>
                        <tr class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Name</th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Question</th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Gold Answer</th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Created</th>
                            <th class="px-6 py-3 text-right text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Actions</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        {% for benchmark in benchmarks %}
                        <tr class="hover:bg-gray-50 dark:hover:bg-gray-700 dark:bg-gray-800 transition-colors">
                            <td class="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">{{ benchmark.name }}</td>
                            <td class="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{{ benchmark.question | truncate(50) }}</td>
                            <td class="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{{ benchmark.gold_answer | truncate(50) }}</td>
                            <td class="px-6 py-4 text-sm text-gray-500 dark:text-gray-400"><span data-utc="{{ benchmark.created_at }}" data-format="date">{{ benchmark.created_at[:10] }}</span></td>
                            <td class="px-6 py-4">
                                <div class="flex items-center justify-end gap-2">
                                    <a href="/benchmarks/{{ benchmark.id }}/evaluate" class="text-sm font-medium text-amber-600 hover:text-amber-800">Evaluate</a>
                                    <span class="text-gray-300">|</span>
                                    <a href="/benchmarks/{{ benchmark.id }}/results" class="text-sm font-medium text-primary-600 hover:text-primary-800">Results</a>
                                    <span class="text-gray-300">|</span>
                                    <form action="/benchmarks/{{ benchmark.id }}/delete" method="post" class="inline">
                                        <button type="submit" class="text-sm font-medium text-red-500 hover:text-red-700">Delete</button>
                                    </form>
                                </div>
                            </td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="5" class="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
                                <div class="flex flex-col items-center">
                                    <svg class="w-12 h-12 text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
                                    <p>No benchmarks created yet</p>
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endblock %}""",
    )
)

BENCHMARK_EVALUATE_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Evaluate - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="max-w-2xl mx-auto">
            <div class="mb-6">
                <div class="flex items-center gap-3 mb-2">
                    <span class="badge badge-blue">{{ benchmark.name }}</span>
                    <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Run Evaluation</h1>
                </div>
            </div>
            
            <div class="section-card mb-6">
                <div class="section-header">
                    <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    <h2 class="section-title">Benchmark Details</h2>
                </div>
                <div class="section-body space-y-3">
                    <div>
                        <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">Question</p>
                        <p class="text-sm text-gray-900 dark:text-gray-100 bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">{{ benchmark.question }}</p>
                    </div>
                    <div>
                        <p class="text-xs font-medium text-emerald-600 uppercase mb-1">Gold Answer</p>
                        <p class="text-sm text-gray-900 dark:text-gray-100 bg-emerald-50 dark:bg-emerald-900/30 p-3 rounded-lg border border-emerald-200 dark:border-emerald-800">{{ benchmark.gold_answer }}</p>
                    </div>
                </div>
            </div>
            
            <form action="/benchmarks/{{ benchmark.id }}/evaluate" method="post" class="space-y-6" id="eval-form">
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path></svg>
                        <h2 class="section-title">Select Experiment</h2>
                    </div>
                    <div class="section-body">
                        <div class="form-group">
                            <label class="form-label">Completed Experiment</label>
                            <select name="experiment_id" required class="form-select">
                                <option value="">-- Select an experiment --</option>
                                {% for exp in experiments %}
                                {% if exp.status == 'completed' %}
                                <option value="{{ exp.id }}">{{ exp.id[:8] }} - {{ exp.config.model.pretrained_model_name | truncate(30) }} ({{ exp.dataset_filename }})</option>
                                {% endif %}
                                {% endfor %}
                            </select>
                            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Only completed experiments with trained models are shown</p>
                        </div>
                    </div>
                </div>
                
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                        <h2 class="section-title">Generation Settings</h2>
                    </div>
                    <div class="section-body">
                        <div class="grid grid-cols-3 gap-4">
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Max New Tokens
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Maximum number of tokens to generate in the response. Longer answers need more tokens. Range: 32-512</span></span>
                                </label>
                                <input type="number" name="max_new_tokens" value="128" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Temperature
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Controls randomness in generation. 0.0 = deterministic, 1.0 = creative. Lower values for factual answers.</span></span>
                                </label>
                                <input type="number" name="temperature" value="0.7" step="0.1" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label flex items-center gap-1">Top-P
                                    <span class="group relative"><svg class="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span class="tooltip-content">Nucleus sampling threshold. Only consider tokens with cumulative probability up to top_p. Range: 0.0-1.0, typical: 0.9</span></span>
                                </label>
                                <input type="number" name="top_p" value="0.9" step="0.05" class="form-input">
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="flex justify-end gap-3">
                    <a href="/benchmarks" class="px-4 py-2 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-100 rounded-lg transition-all">Cancel</a>
                    <button type="submit" id="eval-submit-btn" class="btn-primary px-8">Start Evaluation</button>
                </div>
            </form>
            
            <!-- Evaluation Modal -->
            <div id="eval-modal" class="fixed inset-0 bg-gray-900/50 dark:bg-gray-900/80 backdrop-blur-sm hidden items-center justify-center z-50">
                <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl p-8 max-w-md mx-4 text-center border border-gray-200 dark:border-gray-700">
                    <div class="w-16 h-16 mx-auto mb-4">
                        <svg class="animate-spin w-16 h-16 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                    </div>
                    <h3 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2">Running Evaluation</h3>
                    <p class="text-gray-600 dark:text-gray-300 mb-4">Generating model response and calculating ROUGE score...</p>
                    <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mb-4 overflow-hidden">
                        <div class="bg-blue-600 dark:bg-blue-500 h-2 rounded-full animate-pulse" style="width: 100%"></div>
                    </div>
                    <div class="text-sm text-gray-500 dark:text-gray-400">
                        <p>This typically takes 30 seconds to 2 minutes</p>
                        <p>depending on model size and generation settings.</p>
                    </div>
                </div>
            </div>
            
            <script>
            document.addEventListener('DOMContentLoaded', function() {
                const form = document.getElementById('eval-form');
                const modal = document.getElementById('eval-modal');
                const submitBtn = document.getElementById('eval-submit-btn');
                const statusText = document.getElementById('eval-status-text');
                
                if (form && modal) {
                    form.addEventListener('submit', async function(e) {
                        e.preventDefault();
                        
                        modal.classList.remove('hidden');
                        modal.classList.add('flex');
                        submitBtn.disabled = true;
                        submitBtn.textContent = 'Running...';
                        
                        const formData = new FormData(form);
                        try {
                            // Start the evaluation
                            const resp = await fetch(form.action, {
                                method: 'POST',
                                body: formData,
                                headers: { 'X-Requested-With': 'XMLHttpRequest' }
                            });
                            const data = await resp.json();
                            
                            if (!data.eval_id) {
                                throw new Error(data.detail || 'Failed to start evaluation');
                            }
                            
                            const evalId = data.eval_id;
                            const benchmarkId = data.benchmark_id;
                            
                            // Poll for completion
                            const pollInterval = 2000; // 2 seconds
                            const maxPolls = 300; // 10 minutes max
                            let polls = 0;
                            
                            const poll = async () => {
                                polls++;
                                const statusResp = await fetch('/api/evaluations/' + evalId);
                                const statusData = await statusResp.json();
                                
                                if (statusData.status === 'completed' || statusData.status === 'failed') {
                                    window.location.href = '/benchmarks/' + benchmarkId + '/results';
                                    return;
                                }
                                
                                if (polls >= maxPolls) {
                                    alert('Evaluation timed out. Check results page for status.');
                                    window.location.href = '/benchmarks/' + benchmarkId + '/results';
                                    return;
                                }
                                
                                setTimeout(poll, pollInterval);
                            };
                            
                            poll();
                        } catch (err) {
                            modal.classList.add('hidden');
                            modal.classList.remove('flex');
                            submitBtn.disabled = false;
                            submitBtn.textContent = 'Start Evaluation';
                            alert('Evaluation failed: ' + err.message);
                        }
                    });
                }
            });
            </script>
        </div>
        {% endblock %}""",
    )
)

BENCHMARK_RESULTS_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Benchmark Results - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="flex items-center justify-between mb-6">
            <div>
                <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Evaluation Results</h1>
                <p class="text-gray-600 dark:text-gray-400">Benchmark: <span class="font-medium">{{ benchmark.name }}</span></p>
            </div>
            <a href="/benchmarks" class="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white">&larr; Back to Benchmarks</a>
        </div>
        
        <div class="section-card mb-6">
            <div class="section-header">
                <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                <h2 class="section-title">Benchmark Details</h2>
            </div>
            <div class="section-body space-y-3">
                <div>
                    <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">Question</p>
                    <p class="text-sm text-gray-900 dark:text-gray-100 bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">{{ benchmark.question }}</p>
                </div>
                <div>
                    <p class="text-xs font-medium text-emerald-600 uppercase mb-1">Gold Answer</p>
                    <p class="text-sm text-gray-900 dark:text-gray-100 bg-emerald-50 dark:bg-emerald-900/30 p-3 rounded-lg border border-emerald-200 dark:border-emerald-800">{{ benchmark.gold_answer }}</p>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <h2 class="font-semibold text-gray-800 dark:text-gray-200">Evaluation Runs</h2>
            </div>
            <div class="divide-y divide-gray-100">
                {% for eval in evaluations %}
                <div class="p-6">
                    <div class="flex items-center justify-between mb-4">
                        <div class="flex items-center gap-3">
                            <span class="font-mono text-sm text-gray-500 dark:text-gray-400">{{ eval.id[:8] }}</span>
                            {% if eval.status == 'completed' %}
                            <span class="badge badge-green">Completed</span>
                            {% elif eval.status == 'running' %}
                            <span class="badge badge-blue">Running</span>
                            {% elif eval.status == 'failed' %}
                            <span class="badge badge-red">Failed</span>
                            {% else %}
                            <span class="badge badge-gray">Pending</span>
                            {% endif %}
                            <form action="/evaluations/{{ eval.id }}/delete" method="post" class="inline" onsubmit="return confirm('Delete this evaluation?')">
                                <button type="submit" class="btn-danger">Delete</button>
                            </form>
                        </div>
                        <div class="text-right">
                            {% if eval.status == 'completed' %}
                            <p class="text-3xl font-bold {% if eval.rouge_score > 50 %}text-emerald-600{% elif eval.rouge_score > 20 %}text-amber-600{% else %}text-red-600{% endif %}">{{ "%.2f"|format(eval.rouge_score) }}</p>
                            <p class="text-xs text-gray-500 dark:text-gray-400 uppercase">ROUGE Score</p>
                            {% endif %}
                        </div>
                    </div>
                    <div class="text-sm text-gray-500 dark:text-gray-400 mb-3">
                        Experiment: <span class="font-mono">{{ eval.experiment_id[:8] }}</span> • <span data-utc="{{ eval.started_at }}">{{ eval.started_at[:16] }}</span>
                    </div>
                    {% if eval.status == 'completed' %}
                    <div>
                        <p class="text-xs font-medium text-blue-600 uppercase mb-1">Model Answer</p>
                        <p class="text-sm text-gray-900 dark:text-gray-100 bg-blue-50 dark:bg-blue-900/30 p-3 rounded-lg border border-blue-200 dark:border-blue-800">{{ eval.model_answer }}</p>
                    </div>
                    {% endif %}
                    {% if eval.error %}
                    <div class="mt-3 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg">
                        <p class="text-sm text-red-700">{{ eval.error }}</p>
                    </div>
                    {% endif %}
                </div>
                {% else %}
                <div class="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
                    <p>No evaluations run yet. <a href="/benchmarks/{{ benchmark.id }}/evaluate" class="text-primary-600 hover:text-primary-800">Run one now →</a></p>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endblock %}""",
    )
)

EVALUATION_DETAIL_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Evaluation Details - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="flex items-center justify-between mb-6">
            <div class="flex items-center gap-3">
                <span class="badge badge-blue">{{ evaluation.benchmark_name }}</span>
                <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Evaluation Details</h1>
            </div>
            <a href="/benchmarks" class="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white">&larr; Back to Benchmarks</a>
        </div>
        
        <!-- Summary Card -->
        <div class="card mb-6">
            <div class="card-body">
                <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
                    <div>
                        <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">Status</p>
                        {% if evaluation.status == 'completed' %}
                        <span class="badge badge-green">Completed</span>
                        {% elif evaluation.status == 'running' %}
                        <span class="badge badge-blue">Running</span>
                        {% elif evaluation.status == 'failed' %}
                        <span class="badge badge-red">Failed</span>
                        {% else %}
                        <span class="badge badge-gray">Pending</span>
                        {% endif %}
                    </div>
                    <div>
                        <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">Experiment</p>
                        <a href="/experiments/{{ evaluation.experiment_id }}" class="font-mono text-sm text-primary-600 hover:text-primary-800 hover:underline">{{ evaluation.experiment_id[:8] }}...</a>
                    </div>
                    <div>
                        <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">Started</p>
                        <p class="text-sm text-gray-900 dark:text-gray-100"><span data-utc="{{ evaluation.started_at }}">{{ evaluation.started_at[:19] }}</span></p>
                    </div>
                    <div>
                        <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">Completed</p>
                        <p class="text-sm text-gray-900 dark:text-gray-100">{% if evaluation.completed_at %}<span data-utc="{{ evaluation.completed_at }}">{{ evaluation.completed_at[:19] }}</span>{% else %}In progress...{% endif %}</p>
                    </div>
                </div>
                {% if evaluation.error %}
                <div class="mt-4 p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg">
                    <p class="text-sm font-medium text-red-800">Error</p>
                    <p class="text-sm text-red-700 mt-1">{{ evaluation.error }}</p>
                </div>
                {% endif %}
            </div>
        </div>
        
        <!-- ROUGE Score -->
        {% if evaluation.status == 'completed' %}
        <div class="metric-card mb-6 text-center py-8">
            <p class="metric-label mb-2">ROUGE-L Score</p>
            <p class="text-5xl font-bold {% if evaluation.rouge_score > 50 %}text-emerald-600{% elif evaluation.rouge_score > 20 %}text-amber-600{% else %}text-red-600{% endif %}">{{ "%.2f"|format(evaluation.rouge_score) }}</p>
        </div>
        {% endif %}
        
        <!-- Q&A Comparison -->
        <div class="card">
            <div class="card-header">
                <h2 class="font-semibold text-gray-800 dark:text-gray-200">Question & Answer Comparison</h2>
            </div>
            <div class="card-body space-y-4">
                <div>
                    <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">Question</p>
                    <p class="text-sm text-gray-900 dark:text-gray-100 bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">{{ evaluation.question }}</p>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <p class="text-xs font-medium text-emerald-600 uppercase mb-1">Gold Answer</p>
                        <p class="text-sm text-gray-900 dark:text-gray-100 bg-emerald-50 dark:bg-emerald-900/30 p-3 rounded-lg border border-emerald-200 dark:border-emerald-800 min-h-24">{{ evaluation.gold_answer }}</p>
                    </div>
                    <div>
                        <p class="text-xs font-medium text-blue-600 uppercase mb-1">Model Answer</p>
                        <p class="text-sm text-gray-900 dark:text-gray-100 bg-blue-50 dark:bg-blue-900/30 p-3 rounded-lg border border-blue-200 dark:border-blue-800 min-h-24">{{ evaluation.model_answer or 'Pending...' }}</p>
                    </div>
                </div>
            </div>
        </div>
        {% endblock %}""",
    )
)


EVALUATIONS_COMPARE_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Evaluations - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="mb-6">
            <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Model Benchmark Comparisons</h1>
            <p class="text-gray-600 dark:text-gray-400">Compare ROUGE scores and settings across all evaluated models</p>
        </div>
        
        {% if evaluations %}
        <div class="card mb-6">
            <div class="card-header flex items-center justify-between">
                <h2 class="font-semibold text-gray-800 dark:text-gray-200">ROUGE Score Leaderboard</h2>
                <div class="flex items-center gap-4">
                    <span id="eval-count" class="text-sm text-gray-500 dark:text-gray-400">{{ evaluations | length }} evaluation(s)</span>
                    <span id="selected-count" class="text-sm text-primary-600 hidden">0 selected</span>
                    <button id="compare-btn" class="btn-primary text-sm px-3 py-1.5 hidden" onclick="compareSelected()">
                        <span class="flex items-center gap-1.5">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
                            Compare Configs
                        </span>
                    </button>
                    <button id="clear-filters" class="text-xs text-primary-600 hover:text-primary-800 hidden">Clear Filters</button>
                </div>
            </div>
            
            <!-- Filter Row -->
            <div class="px-4 py-3 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700">
                <div class="grid grid-cols-12 gap-2 text-xs">
                    <div class="flex items-center justify-center">
                        <input type="checkbox" id="select-all" class="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" title="Select all">
                    </div>
                    <div></div>
                    <div><input type="text" id="filter-rouge" placeholder="ROUGE..." class="w-full px-2 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"></div>
                    <div><input type="text" id="filter-benchmark" placeholder="Benchmark..." class="w-full px-2 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"></div>
                    <div><input type="text" id="filter-model" placeholder="Model..." class="w-full px-2 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"></div>
                    <div><input type="text" id="filter-dataset" placeholder="Dataset..." class="w-full px-2 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"></div>
                    <div><input type="text" id="filter-lr" placeholder="LR..." class="w-full px-2 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"></div>
                    <div><input type="text" id="filter-epochs" placeholder="Epochs..." class="w-full px-2 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"></div>
                    <div><input type="text" id="filter-batch" placeholder="Batch..." class="w-full px-2 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"></div>
                    <div><input type="text" id="filter-lora" placeholder="LoRA..." class="w-full px-2 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"></div>
                    <div><input type="text" id="filter-started" placeholder="Started..." class="w-full px-2 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"></div>
                    <div></div>
                </div>
            </div>
            
            <div class="overflow-x-auto">
                <table class="w-full" id="eval-table">
                    <thead>
                        <tr class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                            <th class="px-3 py-3 text-center text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider w-10"></th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700" data-sort="rank">Rank <span class="sort-icon"></span></th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700" data-sort="rouge">ROUGE <span class="sort-icon">▼</span></th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700" data-sort="benchmark">Benchmark <span class="sort-icon"></span></th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700" data-sort="model">Model <span class="sort-icon"></span></th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700" data-sort="dataset">Dataset <span class="sort-icon"></span></th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700" data-sort="lr">LR <span class="sort-icon"></span></th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700" data-sort="epochs">Epochs <span class="sort-icon"></span></th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700" data-sort="batch">Batch <span class="sort-icon"></span></th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700" data-sort="lora">LoRA <span class="sort-icon"></span></th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700" data-sort="started">Started <span class="sort-icon"></span></th>
                            <th class="px-4 py-3 text-right text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Actions</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100" id="eval-tbody">
                        {% for eval in evaluations %}
                        <tr class="hover:bg-gray-50 dark:hover:bg-gray-700 dark:bg-gray-800 transition-colors eval-row"
                            data-rank="{{ loop.index }}"
                            data-rouge="{{ eval.rouge_score }}"
                            data-benchmark="{{ eval.benchmark_name }}"
                            data-model="{{ eval.model_name }}"
                            data-dataset="{{ eval.dataset_filename }}"
                            data-lr="{{ eval.learning_rate }}"
                            data-epochs="{{ eval.num_epochs }}"
                            data-batch="{{ eval.batch_size }}"
                            data-lora="{% if eval.lora_r %}r={{ eval.lora_r }} α={{ eval.lora_alpha }}{% endif %}"
                            data-started="{{ eval.started_at[:19] if eval.started_at else '' }}"
                            data-experiment-id="{{ eval.experiment_id }}">
                            <td class="px-3 py-4 text-center">
                                <input type="checkbox" class="eval-checkbox w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" data-experiment-id="{{ eval.experiment_id }}">
                            </td>
                            <td class="px-4 py-4">
                                {% if loop.index == 1 %}
                                <span class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-yellow-100 text-yellow-700 font-bold">1</span>
                                {% elif loop.index == 2 %}
                                <span class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-gray-200 text-gray-700 dark:text-gray-300 font-bold">2</span>
                                {% elif loop.index == 3 %}
                                <span class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-amber-100 text-amber-700 font-bold">3</span>
                                {% else %}
                                <span class="text-gray-500 dark:text-gray-400 font-medium pl-2">{{ loop.index }}</span>
                                {% endif %}
                            </td>
                            <td class="px-4 py-4">
                                <span class="text-xl font-bold {% if eval.rouge_score > 50 %}text-emerald-600{% elif eval.rouge_score > 20 %}text-amber-600{% else %}text-red-600{% endif %}">{{ "%.2f"|format(eval.rouge_score) }}</span>
                            </td>
                            <td class="px-4 py-4">
                                <span class="font-medium text-gray-900 dark:text-gray-100">{{ eval.benchmark_name }}</span>
                            </td>
                            <td class="px-4 py-4">
                                <span class="text-sm font-mono text-gray-700 dark:text-gray-300" title="{{ eval.model_name }}">{{ eval.model_name | truncate(30) }}</span>
                            </td>
                            <td class="px-4 py-4">
                                <span class="text-sm text-gray-600 dark:text-gray-400" title="{{ eval.dataset_filename }}">{{ eval.dataset_filename | truncate(20) }}</span>
                            </td>
                            <td class="px-4 py-4">
                                <span class="text-sm font-mono text-gray-600 dark:text-gray-400">{{ "%.0e"|format(eval.learning_rate) }}</span>
                            </td>
                            <td class="px-4 py-4">
                                <span class="text-sm text-gray-600 dark:text-gray-400">{{ eval.num_epochs }}</span>
                            </td>
                            <td class="px-4 py-4">
                                <span class="text-sm text-gray-600 dark:text-gray-400">{{ eval.batch_size }}</span>
                            </td>
                            <td class="px-4 py-4">
                                {% if eval.lora_r %}
                                <span class="badge badge-blue">r={{ eval.lora_r }} α={{ eval.lora_alpha }}</span>
                                {% else %}
                                <span class="text-sm text-gray-400">—</span>
                                {% endif %}
                            </td>
                            <td class="px-4 py-4">
                                {% if eval.started_at %}<span class="text-sm text-gray-600 dark:text-gray-400" data-utc="{{ eval.started_at }}">{{ eval.started_at[:16].replace('T', ' ') }}</span>{% else %}<span class="text-sm text-gray-600 dark:text-gray-400">—</span>{% endif %}
                            </td>
                            <td class="px-4 py-4 text-right whitespace-nowrap">
                                <a href="/experiments/{{ eval.experiment_id }}" class="text-sm font-medium text-purple-600 hover:text-purple-800 mr-3">Experiment</a>
                                <a href="/evaluations/{{ eval.eval_id }}" class="text-sm font-medium text-primary-600 hover:text-primary-800 mr-3">Details</a>
                                <form action="/evaluations/{{ eval.eval_id }}/delete" method="post" class="inline" onsubmit="return confirm('Delete this evaluation?')">
                                    <button type="submit" class="text-sm font-medium text-red-500 hover:text-red-700">Delete</button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Settings Comparison Summary -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="metric-card">
                <p class="metric-label mb-2">Best ROUGE Score</p>
                <p class="metric-value">{{ "%.2f"|format(evaluations[0].rouge_score) if evaluations else "—" }}</p>
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{{ evaluations[0].model_name | truncate(25) if evaluations else "" }}</p>
            </div>
            <div class="metric-card">
                <p class="metric-label mb-2">Models Evaluated</p>
                <p class="metric-value">{{ evaluations | map(attribute='model_name') | unique | list | length }}</p>
            </div>
            <div class="metric-card">
                <p class="metric-label mb-2">Benchmarks Used</p>
                <p class="metric-value">{{ evaluations | map(attribute='benchmark_name') | unique | list | length }}</p>
            </div>
        </div>
        
        <script>
        // Global compare function
        function compareSelected() {
            const checkboxes = document.querySelectorAll('.eval-checkbox:checked');
            const experimentIds = [...new Set([...checkboxes].map(cb => cb.dataset.experimentId))];
            if (experimentIds.length < 2) {
                alert('Please select at least 2 experiments to compare');
                return;
            }
            window.location.href = '/experiments/compare?ids=' + experimentIds.join(',');
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            const table = document.getElementById('eval-table');
            const tbody = document.getElementById('eval-tbody');
            const countSpan = document.getElementById('eval-count');
            const selectedSpan = document.getElementById('selected-count');
            const compareBtn = document.getElementById('compare-btn');
            const clearBtn = document.getElementById('clear-filters');
            const selectAll = document.getElementById('select-all');
            const headers = table.querySelectorAll('th[data-sort]');
            
            let currentSort = { col: 'rouge', dir: 'desc' };
            
            // Filter inputs
            const filters = {
                rouge: document.getElementById('filter-rouge'),
                benchmark: document.getElementById('filter-benchmark'),
                model: document.getElementById('filter-model'),
                dataset: document.getElementById('filter-dataset'),
                lr: document.getElementById('filter-lr'),
                epochs: document.getElementById('filter-epochs'),
                batch: document.getElementById('filter-batch'),
                lora: document.getElementById('filter-lora'),
                started: document.getElementById('filter-started')
            };
            
            // Checkbox selection handling
            function updateSelectionUI() {
                const checkboxes = document.querySelectorAll('.eval-checkbox:checked');
                const count = checkboxes.length;
                const uniqueExps = [...new Set([...checkboxes].map(cb => cb.dataset.experimentId))];
                
                if (count > 0) {
                    selectedSpan.textContent = uniqueExps.length + ' experiment(s) selected';
                    selectedSpan.classList.remove('hidden');
                } else {
                    selectedSpan.classList.add('hidden');
                }
                
                if (uniqueExps.length >= 2) {
                    compareBtn.classList.remove('hidden');
                } else {
                    compareBtn.classList.add('hidden');
                }
                
                // Update select-all state
                const allCheckboxes = document.querySelectorAll('.eval-checkbox');
                selectAll.checked = allCheckboxes.length > 0 && checkboxes.length === allCheckboxes.length;
                selectAll.indeterminate = checkboxes.length > 0 && checkboxes.length < allCheckboxes.length;
            }
            
            // Select all handler
            selectAll.addEventListener('change', function() {
                const checkboxes = document.querySelectorAll('.eval-checkbox');
                checkboxes.forEach(cb => cb.checked = this.checked);
                updateSelectionUI();
            });
            
            // Individual checkbox handlers
            tbody.addEventListener('change', function(e) {
                if (e.target.classList.contains('eval-checkbox')) {
                    updateSelectionUI();
                }
            });
            
            function applyFilters() {
                const rows = tbody.querySelectorAll('.eval-row');
                let visibleCount = 0;
                let hasFilters = false;
                
                rows.forEach(row => {
                    let visible = true;
                    for (const [key, input] of Object.entries(filters)) {
                        const val = input.value.toLowerCase().trim();
                        if (val) {
                            hasFilters = true;
                            const cellVal = (row.dataset[key] || '').toLowerCase();
                            if (!cellVal.includes(val)) {
                                visible = false;
                                break;
                            }
                        }
                    }
                    row.style.display = visible ? '' : 'none';
                    if (visible) visibleCount++;
                });
                
                countSpan.textContent = visibleCount + ' evaluation(s)' + (hasFilters ? ' (filtered)' : '');
                clearBtn.classList.toggle('hidden', !hasFilters);
            }
            
            function sortTable(col, dir) {
                const rows = Array.from(tbody.querySelectorAll('.eval-row'));
                rows.sort((a, b) => {
                    let aVal = a.dataset[col] || '';
                    let bVal = b.dataset[col] || '';
                    
                    // Numeric columns
                    if (['rank', 'rouge', 'lr', 'epochs', 'batch'].includes(col)) {
                        aVal = parseFloat(aVal) || 0;
                        bVal = parseFloat(bVal) || 0;
                        return dir === 'asc' ? aVal - bVal : bVal - aVal;
                    }
                    
                    // String columns
                    aVal = aVal.toLowerCase();
                    bVal = bVal.toLowerCase();
                    if (dir === 'asc') {
                        return aVal.localeCompare(bVal);
                    } else {
                        return bVal.localeCompare(aVal);
                    }
                });
                
                rows.forEach(row => tbody.appendChild(row));
                
                // Update sort icons
                headers.forEach(h => {
                    const icon = h.querySelector('.sort-icon');
                    if (h.dataset.sort === col) {
                        icon.textContent = dir === 'asc' ? '▲' : '▼';
                    } else {
                        icon.textContent = '';
                    }
                });
            }
            
            // Click handlers for sorting
            headers.forEach(header => {
                header.addEventListener('click', () => {
                    const col = header.dataset.sort;
                    let dir = 'desc';
                    if (currentSort.col === col && currentSort.dir === 'desc') {
                        dir = 'asc';
                    }
                    currentSort = { col, dir };
                    sortTable(col, dir);
                });
            });
            
            // Filter input handlers
            Object.values(filters).forEach(input => {
                input.addEventListener('input', applyFilters);
            });
            
            // Clear filters
            clearBtn.addEventListener('click', () => {
                Object.values(filters).forEach(input => input.value = '');
                applyFilters();
            });
        });
        </script>
        {% else %}
        <div class="card">
            <div class="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
                <div class="flex flex-col items-center">
                    <svg class="w-12 h-12 text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
                    <p class="mb-2">No completed evaluations yet</p>
                    <a href="/benchmarks" class="text-primary-600 hover:text-primary-800">Create a benchmark and run evaluations →</a>
                </div>
            </div>
        </div>
        {% endif %}
        {% endblock %}""",
    )
)

EXPERIMENTS_COMPARE_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Compare Experiments - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <style>
            .diff-same { background-color: transparent; }
            .diff-different { background-color: rgba(251, 191, 36, 0.15); }
            .diff-value { font-family: ui-monospace, monospace; font-size: 0.75rem; }
            .config-section { border-left: 3px solid; padding-left: 0.75rem; margin-bottom: 1rem; }
            .config-section.data { border-color: #3b82f6; }
            .config-section.model { border-color: #8b5cf6; }
            .config-section.training { border-color: #10b981; }
            .config-section.peft { border-color: #f59e0b; }
            .exp-col-0 { color: #3b82f6; }
            .exp-col-1 { color: #8b5cf6; }
            .exp-col-2 { color: #10b981; }
            .exp-col-3 { color: #f59e0b; }
            .exp-col-4 { color: #ef4444; }
            .exp-col-5 { color: #06b6d4; }
        </style>
        
        <div class="flex items-center justify-between mb-6">
            <div>
                <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Compare Experiments</h1>
                <p class="text-gray-600 dark:text-gray-400">Side-by-side config comparison of {{ experiments | length }} experiments</p>
            </div>
            <a href="/evaluations" class="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white">&larr; Back to Evaluations</a>
        </div>
        
        <!-- Experiment Summary Cards -->
        <div class="grid grid-cols-1 md:grid-cols-{{ experiments | length }} gap-4 mb-6">
            {% for exp in experiments %}
            <a href="/experiments/{{ exp.experiment_id }}" class="card hover:ring-2 hover:ring-primary-500 hover:shadow-lg transition-all cursor-pointer block">
                <div class="card-body">
                    <div class="flex items-center gap-2 mb-3">
                        <div class="w-3 h-3 rounded-full exp-col-{{ loop.index0 }}" style="background-color: currentColor;"></div>
                        <span class="font-mono text-sm font-bold exp-col-{{ loop.index0 }}">{{ exp.experiment_id[:8] }}</span>
                    </div>
                    <div class="space-y-2 text-sm">
                        <div class="flex justify-between">
                            <span class="text-gray-500 dark:text-gray-400">Type</span>
                            <span class="font-medium">
                                {% if exp.experiment_type == 'causal_lm' %}
                                <span class="badge badge-green">Causal</span>
                                {% else %}
                                <span class="badge badge-blue">MLM</span>
                                {% endif %}
                            </span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-500 dark:text-gray-400">Dataset</span>
                            <span class="font-medium text-gray-900 dark:text-gray-100">{{ exp.dataset_filename or 'N/A' }}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-500 dark:text-gray-400">Started</span>
                            <span class="font-medium text-gray-900 dark:text-gray-100" data-utc="{{ exp.started_at }}" data-format="date">{{ exp.started_at[:10] }}</span>
                        </div>
                        {% if exp.rouge_scores %}
                        <div class="flex justify-between">
                            <span class="text-gray-500 dark:text-gray-400">Eval ROUGE</span>
                            <span class="font-bold text-lg {% if (exp.rouge_scores | sum / exp.rouge_scores | length) > 50 %}text-emerald-600{% elif (exp.rouge_scores | sum / exp.rouge_scores | length) > 20 %}text-amber-600{% else %}text-red-600{% endif %}">
                                {{ "%.2f"|format(exp.rouge_scores | sum / exp.rouge_scores | length) }}
                            </span>
                        </div>
                        {% endif %}
                        {% if exp.eval_loss is not none %}
                        <div class="flex justify-between">
                            <span class="text-gray-500 dark:text-gray-400">Eval Loss</span>
                            <span class="font-bold text-lg {% if exp.eval_loss < 1.0 %}text-emerald-600{% elif exp.eval_loss < 2.5 %}text-amber-600{% else %}text-red-600{% endif %}">
                                {{ "%.4f"|format(exp.eval_loss) }}
                            </span>
                        </div>
                        {% endif %}
                    </div>
                </div>
            </a>
            {% endfor %}
        </div>
        
        <!-- Config Differences -->
        <div class="card mb-6">
            <div class="card-header flex items-center gap-3">
                <svg class="w-5 h-5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path></svg>
                <h2 class="font-semibold text-gray-800 dark:text-gray-200">Configuration Differences</h2>
                <span class="ml-auto badge badge-amber">{{ config_diff | length }} difference(s)</span>
            </div>
            <div class="card-body">
                {% if config_diff %}
                <div class="overflow-x-auto">
                    <table class="w-full text-sm">
                        <thead>
                            <tr class="border-b border-gray-200 dark:border-gray-700">
                                <th class="px-4 py-3 text-left font-semibold text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-800">Config Key</th>
                                {% for exp in experiments %}
                                <th class="px-4 py-3 text-left font-semibold exp-col-{{ loop.index0 }} bg-gray-50 dark:bg-gray-800">
                                    {{ exp.experiment_id[:8] }}
                                </th>
                                {% endfor %}
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
                            {% for key, values in config_diff.items() %}
                            <tr class="hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-colors diff-different">
                                <td class="px-4 py-3 font-mono text-xs text-gray-700 dark:text-gray-300">
                                    {% set parts = key.split('.') %}
                                    {% if parts[0] == 'data' %}
                                    <span class="inline-block w-2 h-2 rounded-full bg-blue-500 mr-2"></span>
                                    {% elif parts[0] == 'model' %}
                                    <span class="inline-block w-2 h-2 rounded-full bg-purple-500 mr-2"></span>
                                    {% elif parts[0] == 'training' %}
                                    <span class="inline-block w-2 h-2 rounded-full bg-emerald-500 mr-2"></span>
                                    {% elif parts[0] == 'peft' %}
                                    <span class="inline-block w-2 h-2 rounded-full bg-amber-500 mr-2"></span>
                                    {% endif %}
                                    {{ key }}
                                </td>
                                {% for exp in experiments %}
                                <td class="px-4 py-3 diff-value">
                                    {% set val = values.get(exp.experiment_id) %}
                                    {% if val is none %}
                                    <span class="text-gray-400 italic">—</span>
                                    {% elif val is sameas true %}
                                    <span class="text-emerald-600">true</span>
                                    {% elif val is sameas false %}
                                    <span class="text-red-500">false</span>
                                    {% elif val is number %}
                                    <span class="text-blue-600 dark:text-blue-400">{{ val }}</span>
                                    {% elif val is iterable and val is not string %}
                                    <span class="text-purple-600 dark:text-purple-400">[{{ val | join(', ') }}]</span>
                                    {% else %}
                                    <span class="text-gray-900 dark:text-gray-100">{{ val | truncate(30) }}</span>
                                    {% endif %}
                                </td>
                                {% endfor %}
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% else %}
                <div class="text-center py-8 text-gray-500 dark:text-gray-400">
                    <svg class="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    <p>All configurations are identical!</p>
                </div>
                {% endif %}
            </div>
        </div>
        
        <!-- Legend -->
        <div class="card">
            <div class="card-body">
                <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Config Sections</h3>
                <div class="flex flex-wrap gap-4 text-sm">
                    <div class="flex items-center gap-2">
                        <span class="w-3 h-3 rounded-full bg-blue-500"></span>
                        <span class="text-gray-600 dark:text-gray-400">Data</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="w-3 h-3 rounded-full bg-purple-500"></span>
                        <span class="text-gray-600 dark:text-gray-400">Model</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="w-3 h-3 rounded-full bg-emerald-500"></span>
                        <span class="text-gray-600 dark:text-gray-400">Training</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="w-3 h-3 rounded-full bg-amber-500"></span>
                        <span class="text-gray-600 dark:text-gray-400">PEFT/LoRA</span>
                    </div>
                </div>
            </div>
        </div>
        {% endblock %}""",
    )
)

META_FEATURES_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Meta-Learning - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="mb-6 flex items-center justify-between">
            <div>
                <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Meta-Learning</h1>
                <p class="text-gray-600 dark:text-gray-400">Performance prediction using meta-features from training runs</p>
            </div>
            <div class="flex gap-3">
                {% if synthetic_count == 0 %}
                <form action="/meta/generate-synthetic" method="post" class="inline">
                    <button type="submit" class="px-4 py-2 text-sm font-medium text-purple-700 bg-purple-100 rounded-lg hover:bg-purple-200 transition-colors">Generate Synthetic Data</button>
                </form>
                {% else %}
                <form action="/meta/clear-synthetic" method="post" class="inline">
                    <button type="submit" class="px-4 py-2 text-sm font-medium text-red-700 bg-red-100 rounded-lg hover:bg-red-200 transition-colors">Clear Synthetic ({{ synthetic_count }})</button>
                </form>
                {% endif %}
                {% if can_train %}
                <form action="/meta/train" method="post" class="inline">
                    <button type="submit" class="btn-primary">Train Predictor</button>
                </form>
                {% endif %}
            </div>
        </div>
        
        <!-- Predictor Status -->
        <div class="grid grid-cols-1 md:grid-cols-5 gap-6 mb-6">
            <div class="metric-card">
                <p class="metric-label mb-2">Real Experiments</p>
                <p class="metric-value">{{ real_count }}</p>
            </div>
            <div class="metric-card">
                <p class="metric-label mb-2">Synthetic Data</p>
                <p class="metric-value {% if synthetic_count > 0 %}text-purple-600{% endif %}">{{ synthetic_count }}</p>
            </div>
            <div class="metric-card">
                <p class="metric-label mb-2">With ROUGE Scores</p>
                <p class="metric-value">{{ features | selectattr('final_bleu_score') | list | length }}</p>
            </div>
            <div class="metric-card">
                <p class="metric-label mb-2">Predictor Status</p>
                <p class="metric-value text-lg">{% if predictor_trained %}<span class="text-emerald-600">Trained</span>{% else %}<span class="text-amber-600">Not Trained</span>{% endif %}</p>
            </div>
            <div class="metric-card">
                <p class="metric-label mb-2">Min Samples Needed</p>
                <p class="metric-value">5</p>
            </div>
        </div>
        
        {% if importance %}
        <div class="card mb-6">
            <div class="card-header">
                <h2 class="font-semibold text-gray-800 dark:text-gray-200">Feature Importance (Top 10)</h2>
            </div>
            <div class="card-body">
                <div class="space-y-3">
                    {% set max_importance = importance[0][1] if importance and importance[0][1] > 0 else 1 %}
                    {% for name, value in importance[:10] %}
                    <div class="flex items-center gap-4">
                        <span class="w-48 text-sm font-mono text-gray-700 dark:text-gray-300 truncate">{{ name }}</span>
                        <div class="flex-1 bg-gray-100 rounded-full h-4">
                            <div class="bg-purple-500 h-4 rounded-full" style="width: {{ (value / max_importance * 100) | int }}%"></div>
                        </div>
                        <span class="w-20 text-sm text-gray-600 dark:text-gray-400 text-right">{{ "%.1f"|format(value) }}</span>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
        {% endif %}
        
        <div class="card">
            <div class="card-header flex items-center justify-between">
                <h2 class="font-semibold text-gray-800 dark:text-gray-200">Stored Meta-Features</h2>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full">
                    <thead>
                        <tr class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Experiment</th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Model</th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Samples</th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">LR</th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Probe Loss</th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">ROUGE Score</th>
                            <th class="px-4 py-3 text-right text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Actions</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        {% for f in features %}
                        <tr class="hover:bg-gray-50 dark:hover:bg-gray-700 dark:bg-gray-800 transition-colors {% if f.is_synthetic %}bg-purple-50 dark:bg-purple-900/20{% endif %}">
                            <td class="px-4 py-4">
                                <div class="flex items-center gap-2">
                                    <span class="font-mono text-sm text-gray-900 dark:text-gray-100">{{ f.experiment_id[:12] }}...</span>
                                    {% if f.is_synthetic %}<span class="px-1.5 py-0.5 text-xs font-medium rounded bg-purple-100 text-purple-700 dark:bg-purple-800 dark:text-purple-200">SYN</span>{% endif %}
                                </div>
                            </td>
                            <td class="px-4 py-4">
                                <span class="text-sm text-gray-700 dark:text-gray-300">{{ f.model_name | truncate(25) }}</span>
                            </td>
                            <td class="px-4 py-4">
                                <span class="badge badge-blue">{{ f.n_samples }}</span>
                            </td>
                            <td class="px-4 py-4">
                                <span class="text-sm font-mono text-gray-600 dark:text-gray-400">{{ "%.0e"|format(f.learning_rate) }}</span>
                            </td>
                            <td class="px-4 py-4">
                                <span class="text-sm text-gray-600 dark:text-gray-400">{{ "%.3f"|format(f.probe_initial_loss) }} → {{ "%.3f"|format(f.probe_final_loss) }}</span>
                            </td>
                            <td class="px-4 py-4">
                                {% if f.final_bleu_score %}
                                <span class="font-bold {% if f.final_bleu_score > 50 %}text-emerald-600{% elif f.final_bleu_score > 20 %}text-amber-600{% else %}text-red-600{% endif %}">{{ "%.2f"|format(f.final_bleu_score) }}</span>
                                {% else %}
                                <span class="text-gray-400">—</span>
                                {% endif %}
                            </td>
                            <td class="px-4 py-4 text-right">
                                {% if predictor_trained %}
                                <a href="/meta/explain/{{ f.experiment_id }}" class="text-sm font-medium text-purple-600 hover:text-purple-800">Explain</a>
                                {% endif %}
                            </td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="7" class="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
                                <p>No meta-features stored yet. Run probes from the Datasets page.</p>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endblock %}""",
    )
)

META_PROBE_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Run Probe - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="mb-6">
            <div class="flex items-center gap-3 mb-2">
                <span class="px-2.5 py-1 text-xs font-medium rounded-full bg-purple-100 text-purple-700">Meta Probe</span>
                <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Run Training Probe</h1>
            </div>
            <p class="text-gray-600 dark:text-gray-400">
                Dataset: <span class="font-medium text-gray-900 dark:text-gray-100">{{ dataset.filename }}</span>
                <span class="text-gray-400">•</span> {{ dataset.row_count }} rows
                <span class="text-gray-400">•</span> Columns: {{ dataset.columns | join(', ') }}
            </p>
        </div>
        
        <form action="/meta/probe" method="post" id="probe-form">
            <input type="hidden" name="dataset_id" value="{{ dataset.id }}">
            
            <!-- Config Selector -->
            {% if configs %}
            <div class="section-card mb-6">
                <div class="section-header">
                    <svg class="w-5 h-5 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                    <h2 class="section-title">Select Configuration</h2>
                </div>
                <div class="section-body">
                    <div class="flex items-center gap-4">
                        <div class="form-group flex-1">
                            <label class="form-label">Use a saved configuration</label>
                            <select id="config-selector" class="form-select" onchange="handleMetaConfigSelect(this)">
                                <option value="">-- Configure manually --</option>
                                {% for config in configs %}
                                <option value="{{ config.id }}" data-config='{{ config.config | tojson }}'>{{ config.name }} ({{ config.config.model.pretrained_model_name | truncate(30) }})</option>
                                {% endfor %}
                            </select>
                        </div>
                    </div>
                    <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">Select a config to auto-fill form values, or configure manually below.</p>
                </div>
            </div>
            {% endif %}
            
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <!-- Data Config -->
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"></path></svg>
                        <span class="section-title">Data Configuration</span>
                    </div>
                    <div class="section-body space-y-4">
                        <div class="grid grid-cols-2 gap-4">
                            <div class="form-group">
                                <label class="form-label">Question Field</label>
                                <select name="question_field" class="form-select">
                                    {% for col in dataset.columns %}
                                    <option value="{{ col }}" {% if 'question' in col.lower() %}selected{% endif %}>{{ col }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div class="form-group">
                                <label class="form-label">Answer Field</label>
                                <select name="answer_field" class="form-select">
                                    {% for col in dataset.columns %}
                                    <option value="{{ col }}" {% if 'answer' in col.lower() %}selected{% endif %}>{{ col }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                        </div>
                        <div class="form-group">
                            <label class="form-label">System Prompt</label>
                            <textarea name="system_prompt" rows="2" class="form-textarea">You are a helpful AI assistant.</textarea>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Prompt Template</label>
                            <textarea name="template" rows="3" class="form-textarea font-mono text-xs"><|system|>
{system_prompt}
</s>
<|user|>
{question}
</s>
<|assistant|>
{answer}
</s></textarea>
                        </div>
                        <div class="grid grid-cols-2 gap-4">
                            <div class="form-group">
                                <label class="form-label">Max Length</label>
                                <input type="number" name="max_length" value="512" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Probe Steps</label>
                                <input type="number" name="probe_steps" value="10" class="form-input">
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Model & Training Config -->
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                        <span class="section-title">Model & Training</span>
                    </div>
                    <div class="section-body space-y-4">
                        <div class="form-group">
                            <label class="form-label">Model Name</label>
                            <input type="text" name="pretrained_model_name" value="TinyLlama/TinyLlama-1.1B-Chat-v1.0" class="form-input font-mono">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Pad Token Override</label>
                            <input type="text" name="pad_token_override" value="</s>" class="form-input font-mono">
                        </div>
                        <div class="grid grid-cols-2 gap-4">
                            <div class="form-group">
                                <label class="form-label">Learning Rate</label>
                                <input type="text" name="learning_rate" value="2e-5" class="form-input font-mono">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Batch Size</label>
                                <input type="number" name="per_device_train_batch_size" value="1" class="form-input">
                            </div>
                        </div>
                        <div class="grid grid-cols-2 gap-4">
                            <div class="form-group">
                                <label class="form-label">Gradient Accumulation</label>
                                <input type="number" name="gradient_accumulation_steps" value="4" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Warmup Ratio</label>
                                <input type="text" name="warmup_ratio" value="0.03" class="form-input font-mono">
                            </div>
                        </div>
                        
                        <!-- LoRA Settings -->
                        <div class="border-t border-gray-200 dark:border-gray-700 pt-4 mt-4">
                            <div class="flex items-center gap-3 mb-4">
                                <input type="checkbox" name="peft_enabled" id="peft_enabled" class="form-checkbox" checked>
                                <label for="peft_enabled" class="text-sm font-medium text-gray-700 dark:text-gray-300">Enable LoRA</label>
                            </div>
                            <div class="grid grid-cols-2 gap-4">
                                <div class="form-group">
                                    <label class="form-label">LoRA r</label>
                                    <input type="number" name="peft_r" value="8" class="form-input">
                                </div>
                                <div class="form-group">
                                    <label class="form-label">LoRA Alpha</label>
                                    <input type="number" name="peft_lora_alpha" value="16" class="form-input">
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="flex justify-end gap-3 mt-6">
                <a href="/datasets" class="px-4 py-2 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-100 rounded-lg transition-all">Cancel</a>
                <button type="submit" id="run-probe-btn" class="bg-purple-600 text-white px-8 py-2 rounded-lg font-medium hover:bg-purple-700 transition-all duration-200 shadow-sm hover:shadow-md">Run Probe</button>
            </div>
        </form>
        
        <!-- Loading Modal -->
        <div id="loading-modal" class="fixed inset-0 bg-gray-900/50 backdrop-blur-sm hidden items-center justify-center z-50">
            <div class="bg-white rounded-2xl shadow-2xl p-8 max-w-md mx-4 text-center">
                <div class="w-16 h-16 mx-auto mb-4">
                    <svg class="animate-spin w-16 h-16 text-purple-600" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                </div>
                <h3 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2">Running Probe</h3>
                <p class="text-gray-600 dark:text-gray-400 mb-4">Extracting meta-features from training run...</p>
                <div class="w-full bg-gray-200 rounded-full h-2 mb-4 overflow-hidden">
                    <div class="bg-purple-600 h-2 rounded-full animate-pulse" style="width: 100%"></div>
                </div>
                <div class="text-sm text-gray-500 dark:text-gray-400">
                    <p>This typically takes 1-3 minutes depending on</p>
                    <p>model size and probe steps.</p>
                </div>
            </div>
        </div>
        
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Loading modal on form submit
            const form = document.getElementById('probe-form');
            const modal = document.getElementById('loading-modal');
            const submitBtn = document.getElementById('run-probe-btn');
            
            if (form && modal) {
                form.addEventListener('submit', function() {
                    modal.classList.remove('hidden');
                    modal.classList.add('flex');
                    submitBtn.disabled = true;
                    submitBtn.textContent = 'Running...';
                });
            }
            
        });
        
        function handleMetaConfigSelect(select) {
            const option = select.options[select.selectedIndex];
            if (!option.value) return;
            
            try {
                const cfg = JSON.parse(option.dataset.config);
                
                // Data config
                if (cfg.data) {
                    if (cfg.data.question_field) document.querySelector('[name="question_field"]').value = cfg.data.question_field;
                    if (cfg.data.answer_field) document.querySelector('[name="answer_field"]').value = cfg.data.answer_field;
                    if (cfg.data.system_prompt) document.querySelector('[name="system_prompt"]').value = cfg.data.system_prompt;
                    if (cfg.data.template) document.querySelector('[name="template"]').value = cfg.data.template;
                    if (cfg.data.max_length !== undefined) document.querySelector('[name="max_length"]').value = cfg.data.max_length;
                }
                
                // Model config
                if (cfg.model) {
                    if (cfg.model.pretrained_model_name) document.querySelector('[name="pretrained_model_name"]').value = cfg.model.pretrained_model_name;
                    if (cfg.model.pad_token_override) document.querySelector('[name="pad_token_override"]').value = cfg.model.pad_token_override;
                }
                
                // PEFT config
                if (cfg.peft) {
                    document.querySelector('[name="peft_enabled"]').checked = !!cfg.peft.enabled;
                    if (cfg.peft.r !== undefined) document.querySelector('[name="peft_r"]').value = cfg.peft.r;
                    if (cfg.peft.lora_alpha !== undefined) document.querySelector('[name="peft_lora_alpha"]').value = cfg.peft.lora_alpha;
                }
                
                // Training config
                if (cfg.training) {
                    if (cfg.training.learning_rate !== undefined) document.querySelector('[name="learning_rate"]').value = cfg.training.learning_rate;
                    if (cfg.training.per_device_train_batch_size !== undefined) document.querySelector('[name="per_device_train_batch_size"]').value = cfg.training.per_device_train_batch_size;
                    if (cfg.training.gradient_accumulation_steps !== undefined) document.querySelector('[name="gradient_accumulation_steps"]').value = cfg.training.gradient_accumulation_steps;
                    if (cfg.training.warmup_ratio !== undefined) document.querySelector('[name="warmup_ratio"]').value = cfg.training.warmup_ratio;
                }
            } catch (err) {
                console.error('Failed to parse config:', err);
            }
        }
        </script>
        {% endblock %}""",
    )
)

META_PROBE_RESULT_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Probe Results - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="mb-6 flex items-center justify-between">
            <div>
                <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Probe Results</h1>
                <p class="text-gray-600 dark:text-gray-400">Meta-features extracted from {{ features.probe_steps }} training steps</p>
            </div>
            <a href="/meta" class="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white">&larr; Back to Meta</a>
        </div>
        
        {% if prediction is not none %}
        <div class="card mb-6 bg-gradient-to-r from-purple-50 to-white">
            <div class="card-body">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm font-medium text-purple-700 mb-1">Predicted ROUGE Score</p>
                        <p class="text-4xl font-bold text-purple-600">{{ "%.2f"|format(prediction) }}</p>
                    </div>
                    <div class="text-right">
                        <p class="text-sm text-gray-500 dark:text-gray-400">Based on trained predictor</p>
                    </div>
                </div>
            </div>
        </div>
        {% endif %}
        
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- Static Dataset Features -->
            <div class="section-card">
                <div class="section-header">
                    <span class="section-title">Dataset Features</span>
                </div>
                <div class="section-body">
                    <dl class="grid grid-cols-2 gap-4">
                        <div>
                            <dt class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Samples</dt>
                            <dd class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ features.n_samples }}</dd>
                        </div>
                        <div>
                            <dt class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Avg Text Length</dt>
                            <dd class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ "%.0f"|format(features.avg_text_length) }}</dd>
                        </div>
                        <div>
                            <dt class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Vocab Size</dt>
                            <dd class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ features.vocab_size }}</dd>
                        </div>
                        <div>
                            <dt class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Type-Token Ratio</dt>
                            <dd class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ "%.3f"|format(features.type_token_ratio) }}</dd>
                        </div>
                        <div>
                            <dt class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">OOV Rate</dt>
                            <dd class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ "%.3f"|format(features.oov_rate) }}</dd>
                        </div>
                        <div>
                            <dt class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Truncation Rate</dt>
                            <dd class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ "%.3f"|format(features.truncation_rate) }}</dd>
                        </div>
                    </dl>
                </div>
            </div>
            
            <!-- Dynamic Probe Features -->
            <div class="section-card">
                <div class="section-header">
                    <span class="section-title">Probe Features</span>
                </div>
                <div class="section-body">
                    <dl class="grid grid-cols-2 gap-4">
                        <div>
                            <dt class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Initial Loss</dt>
                            <dd class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ "%.4f"|format(features.probe_initial_loss) }}</dd>
                        </div>
                        <div>
                            <dt class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Final Loss</dt>
                            <dd class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ "%.4f"|format(features.probe_final_loss) }}</dd>
                        </div>
                        <div>
                            <dt class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Loss Slope</dt>
                            <dd class="text-lg font-semibold {% if features.probe_loss_slope < 0 %}text-emerald-600{% else %}text-red-600{% endif %}">{{ "%.6f"|format(features.probe_loss_slope) }}</dd>
                        </div>
                        <div>
                            <dt class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Loss Variance</dt>
                            <dd class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ "%.6f"|format(features.probe_loss_variance) }}</dd>
                        </div>
                        <div>
                            <dt class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Grad Norm Mean</dt>
                            <dd class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ "%.4f"|format(features.probe_grad_norm_mean) }}</dd>
                        </div>
                        <div>
                            <dt class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Grad Norm Std</dt>
                            <dd class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ "%.4f"|format(features.probe_grad_norm_std) }}</dd>
                        </div>
                    </dl>
                </div>
            </div>
        </div>
        
        <!-- Config Features -->
        <div class="section-card mt-6">
            <div class="section-header">
                <span class="section-title">Config Features</span>
            </div>
            <div class="section-body">
                <dl class="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                        <dt class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Model</dt>
                        <dd class="text-sm font-mono text-gray-900 dark:text-gray-100 truncate">{{ features.model_name }}</dd>
                    </div>
                    <div>
                        <dt class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Learning Rate</dt>
                        <dd class="text-sm font-mono text-gray-900 dark:text-gray-100">{{ "%.0e"|format(features.learning_rate) }}</dd>
                    </div>
                    <div>
                        <dt class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Batch Size</dt>
                        <dd class="text-sm font-mono text-gray-900 dark:text-gray-100">{{ features.batch_size }}</dd>
                    </div>
                    <div>
                        <dt class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">LoRA</dt>
                        <dd class="text-sm font-mono text-gray-900 dark:text-gray-100">{% if features.lora_enabled %}r={{ features.lora_r }} α={{ features.lora_alpha }}{% else %}Disabled{% endif %}</dd>
                    </div>
                </dl>
            </div>
        </div>
        
        <div class="flex justify-end gap-3 mt-6">
            <a href="/datasets" class="px-4 py-2 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-100 rounded-lg transition-all">Back to Datasets</a>
            <a href="/meta" class="bg-purple-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-purple-700 transition-all">View All Features</a>
        </div>
        {% endblock %}""",
    )
)

META_EXPLAIN_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}SHAP Explanation - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="mb-6 flex items-center justify-between">
            <div>
                <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">SHAP Explanation</h1>
                <p class="text-gray-600 dark:text-gray-400">Feature attributions for experiment <span class="font-mono">{{ experiment_id[:12] }}...</span></p>
            </div>
            <a href="/meta" class="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white">&larr; Back to Meta</a>
        </div>
        
        <div class="card mb-6 bg-gradient-to-r from-purple-50 to-white">
            <div class="card-body">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm font-medium text-purple-700 mb-1">Predicted Performance</p>
                        <p class="text-4xl font-bold text-purple-600">{{ "%.2f"|format(prediction) }}</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card mb-6">
            <div class="card-header">
                <h2 class="font-semibold text-gray-800 dark:text-gray-200">Top Feature Drivers</h2>
            </div>
            <div class="card-body">
                <div class="space-y-4">
                    {% for driver in top_drivers %}
                    <div class="flex items-center gap-4 p-3 rounded-lg {% if driver.direction == 'positive' %}bg-emerald-50 dark:bg-emerald-900/30{% else %}bg-red-50 dark:bg-red-900/30{% endif %}">
                        <div class="flex-shrink-0">
                            {% if driver.direction == 'positive' %}
                            <span class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-emerald-100 text-emerald-700">↑</span>
                            {% else %}
                            <span class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-red-100 text-red-700">↓</span>
                            {% endif %}
                        </div>
                        <div class="flex-1">
                            <p class="font-mono text-sm font-medium text-gray-900 dark:text-gray-100">{{ driver.feature }}</p>
                            <p class="text-xs text-gray-500 dark:text-gray-400">Value: {{ driver.value }}</p>
                        </div>
                        <div class="text-right">
                            <p class="font-bold {% if driver.direction == 'positive' %}text-emerald-600{% else %}text-red-600{% endif %}">{{ "%+.4f"|format(driver.shap_value) }}</p>
                            <p class="text-xs text-gray-500 dark:text-gray-400">SHAP value</p>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <h2 class="font-semibold text-gray-800 dark:text-gray-200">All SHAP Values</h2>
            </div>
            <div class="card-body">
                <div class="space-y-2">
                    {% for name, value in shap_values.items() %}
                    <div class="flex items-center gap-4">
                        <span class="w-48 text-sm font-mono text-gray-700 dark:text-gray-300 truncate">{{ name }}</span>
                        <div class="flex-1 flex items-center">
                            {% if value >= 0 %}
                            <div class="w-1/2"></div>
                            <div class="w-1/2 flex items-center">
                                <div class="bg-emerald-500 h-3 rounded-r" style="width: {{ (value / max_shap * 50) | abs | int }}%"></div>
                            </div>
                            {% else %}
                            <div class="w-1/2 flex items-center justify-end">
                                <div class="bg-red-500 h-3 rounded-l" style="width: {{ (value / max_shap * 50) | abs | int }}%"></div>
                            </div>
                            <div class="w-1/2"></div>
                            {% endif %}
                        </div>
                        <span class="w-20 text-sm font-mono text-right {% if value >= 0 %}text-emerald-600{% else %}text-red-600{% endif %}">{{ "%+.4f"|format(value) }}</span>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
        {% endblock %}""",
    )
)

META_OPTIMIZE_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Config Optimizer - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="mb-6 flex items-center justify-between">
            <div>
                <div class="flex items-center gap-3 mb-2">
                    <span class="px-2.5 py-1 text-xs font-medium rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 text-white">Optimizer</span>
                    <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Config Optimizer</h1>
                </div>
                <p class="text-gray-600 dark:text-gray-400">
                    Dataset: <span class="font-medium text-gray-900 dark:text-gray-100">{{ dataset.filename }}</span>
                    <span class="text-gray-400">•</span> {{ dataset.row_count }} rows
                </p>
            </div>
            <a href="/meta" class="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white">&larr; Back to Meta</a>
        </div>
        
        <form action="/meta/optimize" method="post" id="optimize-form">
            <input type="hidden" name="dataset_id" value="{{ dataset.id }}">
            
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                <!-- Base Config -->
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                        <span class="section-title">Base Configuration</span>
                    </div>
                    <div class="section-body space-y-4">
                        <div class="grid grid-cols-2 gap-4">
                            <div class="form-group">
                                <label class="form-label">Question Field</label>
                                <select name="question_field" class="form-select">
                                    {% for col in dataset.columns %}
                                    <option value="{{ col }}" {% if 'question' in col.lower() %}selected{% endif %}>{{ col }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div class="form-group">
                                <label class="form-label">Answer Field</label>
                                <select name="answer_field" class="form-select">
                                    {% for col in dataset.columns %}
                                    <option value="{{ col }}" {% if 'answer' in col.lower() %}selected{% endif %}>{{ col }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Model</label>
                            <input type="text" name="pretrained_model_name" value="TinyLlama/TinyLlama-1.1B-Chat-v1.0" class="form-input font-mono">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Max Length</label>
                            <input type="number" name="max_length" value="512" class="form-input">
                        </div>
                    </div>
                </div>
                
                <!-- Search Space -->
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                        <span class="section-title">Search Space</span>
                    </div>
                    <div class="section-body space-y-4">
                        <div class="form-group">
                            <label class="form-label">Learning Rates (comma-separated)</label>
                            <input type="text" name="learning_rates" value="1e-5, 2e-5, 5e-5, 1e-4" class="form-input font-mono">
                        </div>
                        <div class="form-group">
                            <label class="form-label">LoRA Ranks (comma-separated)</label>
                            <input type="text" name="lora_r_values" value="4, 8, 16" class="form-input font-mono">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Batch Sizes (comma-separated)</label>
                            <input type="text" name="batch_sizes" value="1, 2" class="form-input font-mono">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Epochs (comma-separated)</label>
                            <input type="text" name="num_epochs" value="1, 2, 3" class="form-input font-mono">
                        </div>
                        <div class="grid grid-cols-2 gap-4">
                            <div class="form-group">
                                <label class="form-label">Probe Steps</label>
                                <input type="number" name="probe_steps" value="10" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Max Candidates</label>
                                <input type="number" name="max_candidates" value="12" class="form-input">
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="flex justify-end gap-3">
                <a href="/meta" class="px-4 py-2 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-100 rounded-lg transition-all">Cancel</a>
                <button type="submit" id="optimize-btn" class="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-8 py-2 rounded-lg font-medium hover:from-purple-700 hover:to-indigo-700 transition-all duration-200 shadow-sm hover:shadow-md">
                    Run Optimization
                </button>
            </div>
        </form>
        
        <!-- Loading Modal -->
        <div id="loading-modal" class="fixed inset-0 bg-gray-900/50 backdrop-blur-sm hidden items-center justify-center z-50">
            <div class="bg-white rounded-2xl shadow-2xl p-8 max-w-md mx-4 text-center">
                <div class="w-16 h-16 mx-auto mb-4">
                    <svg class="animate-spin w-16 h-16 text-purple-600" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                </div>
                <h3 class="text-xl font-bold text-gray-900 mb-2">Running Optimization</h3>
                <p class="text-gray-600 mb-4">Testing different configs with quick probes...</p>
                <div class="w-full bg-gray-200 rounded-full h-2 mb-4 overflow-hidden">
                    <div class="bg-purple-600 h-2 rounded-full animate-pulse" style="width: 100%"></div>
                </div>
                <p class="text-sm text-gray-500">This may take a few minutes</p>
            </div>
        </div>
        
        <script>
            document.getElementById('optimize-form').addEventListener('submit', function() {
                document.getElementById('loading-modal').classList.remove('hidden');
                document.getElementById('loading-modal').classList.add('flex');
            });
        </script>
        {% endblock %}""",
    )
)

META_OPTIMIZE_RESULTS_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Optimization Results - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="mb-6 flex items-center justify-between">
            <div>
                <div class="flex items-center gap-3 mb-2">
                    <span class="px-2.5 py-1 text-xs font-medium rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 text-white">Results</span>
                    <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Optimization Results</h1>
                </div>
                <p class="text-gray-600 dark:text-gray-400">{{ message }}</p>
            </div>
            <a href="/meta" class="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white">&larr; Back to Meta</a>
        </div>
        
        <!-- Best Config -->
        {% if best_config %}
        <div class="card mb-6 border-2 border-emerald-500">
            <div class="card-header bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-900/30 dark:to-teal-900/30">
                <h2 class="font-semibold text-emerald-800 dark:text-emerald-200 flex items-center gap-2">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    Recommended Configuration
                </h2>
            </div>
            <div class="card-body">
                <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
                    <div>
                        <p class="text-sm text-gray-500 dark:text-gray-400 mb-1">Learning Rate</p>
                        <p class="text-lg font-mono font-bold text-gray-900 dark:text-gray-100">{{ "%.0e"|format(best_config.learning_rate) }}</p>
                    </div>
                    <div>
                        <p class="text-sm text-gray-500 dark:text-gray-400 mb-1">LoRA Rank</p>
                        <p class="text-lg font-mono font-bold text-gray-900 dark:text-gray-100">{{ best_config.lora_r }}</p>
                    </div>
                    <div>
                        <p class="text-sm text-gray-500 dark:text-gray-400 mb-1">Batch Size</p>
                        <p class="text-lg font-mono font-bold text-gray-900 dark:text-gray-100">{{ best_config.batch_size }}</p>
                    </div>
                    <div>
                        <p class="text-sm text-gray-500 dark:text-gray-400 mb-1">Epochs</p>
                        <p class="text-lg font-mono font-bold text-gray-900 dark:text-gray-100">{{ best_config.num_epochs }}</p>
                    </div>
                </div>
                <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                    <p class="text-sm text-gray-600 dark:text-gray-400">
                        Predicted ROUGE Score: <span class="text-2xl font-bold text-emerald-600">{{ "%.2f"|format(candidates[0].predicted_bleu) }}</span>
                    </p>
                </div>
            </div>
        </div>
        {% endif %}
        
        <!-- All Candidates -->
        <div class="card">
            <div class="card-header">
                <h2 class="font-semibold text-gray-800 dark:text-gray-200">All Candidates Ranked by Predicted ROUGE</h2>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full">
                    <thead>
                        <tr class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Rank</th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Learning Rate</th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">LoRA r</th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Batch Size</th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Epochs</th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Predicted ROUGE</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
                        {% for c in candidates %}
                        <tr class="{% if loop.index == 1 %}bg-emerald-50 dark:bg-emerald-900/20{% else %}hover:bg-gray-50 dark:hover:bg-gray-700{% endif %} dark:bg-gray-800 transition-colors">
                            <td class="px-4 py-4">
                                {% if loop.index == 1 %}
                                <span class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-emerald-500 text-white font-bold">1</span>
                                {% elif loop.index == 2 %}
                                <span class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-gray-200 font-bold">2</span>
                                {% elif loop.index == 3 %}
                                <span class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-amber-400 text-white font-bold">3</span>
                                {% else %}
                                <span class="text-gray-500 dark:text-gray-400 font-medium pl-2">{{ loop.index }}</span>
                                {% endif %}
                            </td>
                            <td class="px-4 py-4 font-mono text-sm text-gray-900 dark:text-gray-100">{{ "%.0e"|format(c.learning_rate) }}</td>
                            <td class="px-4 py-4 font-mono text-sm text-gray-900 dark:text-gray-100">{{ c.lora_r }}</td>
                            <td class="px-4 py-4 font-mono text-sm text-gray-900 dark:text-gray-100">{{ c.batch_size }}</td>
                            <td class="px-4 py-4 font-mono text-sm text-gray-900 dark:text-gray-100">{{ c.num_epochs }}</td>
                            <td class="px-4 py-4">
                                <span class="font-bold {% if c.predicted_bleu > 50 %}text-emerald-600{% elif c.predicted_bleu > 30 %}text-amber-600{% else %}text-red-600{% endif %}">
                                    {{ "%.2f"|format(c.predicted_bleu) }}
                                </span>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="mt-6 flex justify-center">
            <a href="/meta" class="btn-primary">Back to Meta-Learning</a>
        </div>
        {% endblock %}""",
    )
)

META_OPTIMIZE_PROGRESS_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Optimization Running - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="flex flex-col items-center justify-center min-h-[60vh]">
            <div class="text-center max-w-md">
                <div class="w-20 h-20 mx-auto mb-6">
                    <svg class="animate-spin w-20 h-20 text-purple-600" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                </div>
                <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">Optimization Running</h1>
                <p class="text-gray-600 dark:text-gray-400 mb-4">Testing different hyperparameter configurations...</p>
                <p class="text-sm text-gray-500 dark:text-gray-500 mb-6">Job ID: <span class="font-mono">{{ job_id[:12] }}...</span></p>
                
                <div class="bg-gray-100 dark:bg-gray-800 rounded-lg p-4 mb-6">
                    <p class="text-sm text-gray-600 dark:text-gray-400">
                        Status: <span id="status" class="font-medium text-purple-600">{{ status }}</span>
                    </p>
                    <p class="text-xs text-gray-500 dark:text-gray-500 mt-2">
                        Started: <span data-utc="{{ started_at }}" data-format="datetime">{{ started_at[:19] }}</span>
                    </p>
                </div>
                
                <p class="text-sm text-gray-500 dark:text-gray-500">This page will refresh automatically when complete.</p>
            </div>
        </div>
        
        <script>
            function checkStatus() {
                fetch('/api/optimize/{{ job_id }}/status')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('status').textContent = data.status;
                        if (data.status === 'completed' || data.status === 'failed') {
                            window.location.href = '/meta/optimize/{{ job_id }}/results';
                        }
                    })
                    .catch(err => console.error('Status check failed:', err));
            }
            
            // Poll every 3 seconds
            setInterval(checkStatus, 3000);
        </script>
        {% endblock %}""",
    )
)


@app.route("/")
def index():
    # Fetch stats for workflow guide
    stats = {
        "datasets": 0,
        "models": 0,
        "benchmarks": 0,
        "evals": 0,
        "meta_features": 0,
    }
    datasets = []
    benchmarks = []
    configs = []
    
    try:
        datasets_resp = requests.get(f"{API_BASE_URL}/datasets", timeout=5)
        datasets = datasets_resp.json().get("datasets", [])
        stats["datasets"] = len(datasets)
    except Exception:
        pass
    try:
        experiments_resp = requests.get(f"{API_BASE_URL}/experiments", timeout=5)
        experiments = experiments_resp.json().get("experiments", [])
        stats["models"] = len([e for e in experiments if e.get("status") == "completed"])
    except Exception:
        pass
    try:
        benchmarks_resp = requests.get(f"{API_BASE_URL}/benchmarks", timeout=5)
        benchmarks = benchmarks_resp.json().get("benchmarks", [])
        stats["benchmarks"] = len(benchmarks)
    except Exception:
        pass
    try:
        evals_resp = requests.get(f"{API_BASE_URL}/evaluations", timeout=5)
        stats["evals"] = len(evals_resp.json().get("evaluations", []))
    except Exception:
        pass
    try:
        meta_resp = requests.get(f"{API_BASE_URL}/meta/features", timeout=5)
        stats["meta_features"] = len(meta_resp.json().get("features", []))
    except Exception:
        pass
    try:
        configs_resp = requests.get(f"{API_BASE_URL}/configs", timeout=5)
        configs = configs_resp.json().get("configs", [])
    except Exception:
        pass
    return render_template_string(HOME_TEMPLATE, stats=stats, datasets=datasets, benchmarks=benchmarks, configs=configs)


@app.route("/datasets")
def datasets_page():
    resp = requests.get(f"{API_BASE_URL}/datasets", timeout=10)
    data = resp.json()
    return render_template_string(DATASETS_TEMPLATE, datasets=data.get("datasets", []))


@app.route("/datasets/upload", methods=["POST"])
def upload_dataset():
    file = request.files.get("file")
    if not file:
        return redirect(url_for("datasets_page"))
    files = {"file": (file.filename, file.stream, file.content_type)}
    requests.post(f"{API_BASE_URL}/datasets/upload", files=files, timeout=60)
    return redirect(url_for("datasets_page"))


@app.route("/datasets/<dataset_id>/delete", methods=["POST"])
def delete_dataset(dataset_id: str):
    requests.delete(f"{API_BASE_URL}/datasets/{dataset_id}", timeout=10)
    return redirect(url_for("datasets_page"))


@app.route("/configs")
def configs_page():
    resp = requests.get(f"{API_BASE_URL}/configs", timeout=10)
    data = resp.json()
    return render_template_string(CONFIGS_TEMPLATE, configs=data.get("configs", []))


@app.route("/configs/upload", methods=["POST"])
def upload_config():
    """Upload a YAML config file."""
    file = request.files.get("file")
    if not file:
        return redirect(url_for("configs_page"))
    
    files = {"file": (file.filename, file.stream, file.content_type)}
    resp = requests.post(f"{API_BASE_URL}/configs/upload", files=files, timeout=30)
    
    if resp.status_code == 200:
        config_data = resp.json()
        return redirect(url_for("config_detail", config_id=config_data["id"]))
    return redirect(url_for("configs_page"))


@app.route("/configs/<config_id>")
def config_detail(config_id: str):
    resp = requests.get(f"{API_BASE_URL}/configs/{config_id}", timeout=10)
    if resp.status_code != 200:
        return redirect(url_for("configs_page"))
    config = resp.json()
    return render_template_string(CONFIG_DETAIL_TEMPLATE, config=config)


@app.route("/configs/<config_id>/delete", methods=["POST"])
def delete_config(config_id: str):
    requests.delete(f"{API_BASE_URL}/configs/{config_id}", timeout=10)
    return redirect(url_for("configs_page"))


@app.route("/configs/<config_id>/edit", methods=["GET", "POST"])
def edit_config(config_id: str):
    if request.method == "GET":
        resp = requests.get(f"{API_BASE_URL}/configs/{config_id}", timeout=10)
        if resp.status_code != 200:
            return redirect(url_for("configs_page"))
        config = resp.json()
        return render_template_string(CONFIG_EDIT_TEMPLATE, config=config)
    
    # POST - create new config from form
    form = request.form.to_dict()
    
    # Get original config to determine type
    resp = requests.get(f"{API_BASE_URL}/configs/{config_id}", timeout=10)
    if resp.status_code != 200:
        return redirect(url_for("configs_page"))
    original = resp.json()
    
    new_name = form.get("new_name", "").strip() or None
    
    if original["experiment_type"] == "causal_lm":
        target_modules = [m.strip() for m in form.get("peft_target_modules", "").split(",") if m.strip()]
        config_data = {
            "data": {
                "question_field": form.get("question_field", "question"),
                "answer_field": form.get("answer_field", "answer"),
                "system_prompt": form.get("system_prompt", ""),
                "template": form.get("template", ""),
                "validation_split": float(form.get("validation_split", 0.2)),
                "seed": int(form.get("seed", 42)),
                "max_length": int(form.get("max_length", 512)),
            },
            "model": {
                "pretrained_model_name": form.get("pretrained_model_name", ""),
                "trust_remote_code": False,
                "pad_token_override": form.get("pad_token_override") or None,
            },
            "peft": {
                "enabled": "peft_enabled" in form,
                "r": int(form.get("peft_r", 8)),
                "lora_alpha": int(form.get("peft_lora_alpha", 16)),
                "lora_dropout": float(form.get("peft_lora_dropout", 0.05)),
                "bias": form.get("peft_bias", "none"),
                "target_modules": target_modules or ["q_proj", "k_proj", "v_proj", "o_proj"],
            },
            "training": {
                "num_train_epochs": float(form.get("num_train_epochs", 3)),
                "per_device_train_batch_size": int(form.get("per_device_train_batch_size", 1)),
                "per_device_eval_batch_size": int(form.get("per_device_eval_batch_size", 1)),
                "learning_rate": float(form.get("learning_rate", 2e-5)),
                "weight_decay": float(form.get("weight_decay", 0.0)),
                "warmup_ratio": float(form.get("warmup_ratio", 0.03)),
                "gradient_accumulation_steps": int(form.get("gradient_accumulation_steps", 8)),
                "lr_scheduler_type": form.get("lr_scheduler_type", "cosine"),
                "logging_steps": 10,
                "eval_steps": 50,
                "save_steps": 200,
                "save_total_limit": 2,
                "max_steps": int(form.get("max_steps", -1)),
                "gradient_checkpointing": "gradient_checkpointing" in form,
                "fp16": "fp16" in form,
                "bf16": "bf16" in form,
                "early_stopping_patience": int(form.get("early_stopping_patience")) if form.get("early_stopping_patience") else None,
                "early_stopping_metric": form.get("early_stopping_metric", "eval_loss"),
                "early_stopping_greater_is_better": "early_stopping_greater_is_better" in form,
            },
        }
    else:
        text_fields = [f.strip() for f in form.get("text_fields", "").split(",") if f.strip()]
        config_data = {
            "data": {
                "text_fields": text_fields,
                "separator": form.get("separator", "\n\n").replace("\\n", "\n"),
                "validation_split": float(form.get("validation_split", 0.2)),
                "seed": int(form.get("seed", 42)),
                "max_length": int(form.get("max_length", 256)),
            },
            "model": {
                "pretrained_model_name": form.get("pretrained_model_name", "distilbert-base-uncased"),
                "freeze_embedding": False,
                "freeze_encoder_layers": int(form.get("freeze_encoder_layers", 0)),
            },
            "training": {
                "num_train_epochs": float(form.get("num_train_epochs", 3)),
                "per_device_train_batch_size": int(form.get("per_device_train_batch_size", 8)),
                "per_device_eval_batch_size": int(form.get("per_device_eval_batch_size", 8)),
                "learning_rate": float(form.get("learning_rate", 5e-5)),
                "weight_decay": float(form.get("weight_decay", 0.01)),
                "warmup_ratio": 0.0,
                "logging_steps": 10,
                "eval_steps": 50,
                "save_steps": 200,
                "save_total_limit": 2,
                "gradient_accumulation_steps": 1,
                "max_steps": -1,
                "early_stopping_patience": int(form.get("early_stopping_patience")) if form.get("early_stopping_patience") else None,
                "early_stopping_metric": form.get("early_stopping_metric", "eval_loss"),
                "early_stopping_greater_is_better": "early_stopping_greater_is_better" in form,
            },
        }
    
    payload = {"name": new_name, "config": config_data}
    resp = requests.post(f"{API_BASE_URL}/configs", json=payload, timeout=10)
    
    if resp.status_code == 200:
        new_config = resp.json()
        return redirect(url_for("config_detail", config_id=new_config["id"]))
    return redirect(url_for("configs_page"))


@app.route("/experiments/new/masked-lm")
def new_masked_lm_experiment():
    dataset_id = request.args.get("dataset_id")
    if not dataset_id:
        return redirect(url_for("datasets_page"))
    resp = requests.get(f"{API_BASE_URL}/datasets/{dataset_id}", timeout=10)
    if resp.status_code != 200:
        return redirect(url_for("datasets_page"))
    configs_resp = requests.get(f"{API_BASE_URL}/configs/by-type/masked_lm", timeout=10)
    configs = configs_resp.json().get("configs", []) if configs_resp.status_code == 200 else []
    return render_template_string(NEW_MASKED_LM_TEMPLATE, dataset=resp.json(), configs=configs)


@app.route("/experiments/new/causal-lm")
def new_causal_lm_experiment():
    dataset_id = request.args.get("dataset_id")
    if not dataset_id:
        return redirect(url_for("datasets_page"))
    resp = requests.get(f"{API_BASE_URL}/datasets/{dataset_id}", timeout=10)
    if resp.status_code != 200:
        return redirect(url_for("datasets_page"))
    configs_resp = requests.get(f"{API_BASE_URL}/configs/by-type/causal_lm", timeout=10)
    configs = configs_resp.json().get("configs", []) if configs_resp.status_code == 200 else []
    return render_template_string(NEW_CAUSAL_LM_TEMPLATE, dataset=resp.json(), configs=configs)


@app.route("/experiments/masked-lm", methods=["POST"])
def start_masked_lm():
    form = request.form.to_dict()
    config_id = form.get("config_id")
    
    # If a config was selected, use it; otherwise build from form
    if config_id:
        payload = {
            "dataset_id": form.get("dataset_id"),
            "config_id": config_id,
        }
    else:
        text_fields = [f.strip() for f in form.pop("text_fields", "").split(",") if f.strip()]
        payload = {
            "dataset_id": form.get("dataset_id"),
            "config_name": form.get("config_name") or None,
            "config": {
                "data": {
                    "text_fields": text_fields,
                    "separator": form.get("separator", "\n\n").replace("\\n", "\n"),
                    "validation_split": float(form.get("validation_split", 0.2)),
                    "seed": int(form.get("seed", 42)),
                    "max_length": int(form.get("max_length", 256)),
                },
                "model": {
                    "pretrained_model_name": form.get("pretrained_model_name", "distilbert-base-uncased"),
                    "freeze_embedding": "freeze_embedding" in form,
                    "freeze_encoder_layers": int(form.get("freeze_encoder_layers", 0)),
                },
                "training": {
                    "num_train_epochs": float(form.get("num_train_epochs", 3)),
                    "per_device_train_batch_size": int(form.get("per_device_train_batch_size", 8)),
                    "per_device_eval_batch_size": int(form.get("per_device_eval_batch_size", 8)),
                    "learning_rate": float(form.get("learning_rate", 5e-5)),
                    "weight_decay": float(form.get("weight_decay", 0.01)),
                    "warmup_ratio": float(form.get("warmup_ratio", 0.0)),
                    "gradient_accumulation_steps": int(form.get("gradient_accumulation_steps", 1)),
                    "logging_steps": int(form.get("logging_steps", 10)),
                    "eval_steps": int(form.get("eval_steps", 50)),
                    "save_steps": int(form.get("save_steps", 200)),
                    "save_total_limit": int(form.get("save_total_limit", 2)),
                    "max_steps": int(form.get("max_steps", -1)),
                    "early_stopping_patience": int(form.get("early_stopping_patience")) if form.get("early_stopping_patience") else None,
                    "early_stopping_metric": form.get("early_stopping_metric", "eval_loss"),
                    "early_stopping_greater_is_better": "early_stopping_greater_is_better" in form,
                },
            },
        }
    resp = requests.post(f"{API_BASE_URL}/experiments/masked-lm", json=payload, timeout=10)
    if resp.status_code == 200:
        experiment_id = resp.json().get("experiment_id")
        if experiment_id:
            return redirect(url_for("experiment_detail", experiment_id=experiment_id))
    return redirect(url_for("experiments_page"))


@app.route("/experiments/causal-lm", methods=["POST"])
def start_causal_lm():
    form = request.form.to_dict()
    config_id = form.get("config_id")
    
    # If a config was selected, use it; otherwise build from form
    if config_id:
        payload = {
            "dataset_id": form.get("dataset_id"),
            "config_id": config_id,
        }
    else:
        target_modules = [m.strip() for m in form.get("peft_target_modules", "").split(",") if m.strip()]
        payload = {
            "dataset_id": form.get("dataset_id"),
            "config_name": form.get("config_name") or None,
            "config": {
                "data": {
                    "question_field": form.get("question_field", "question"),
                    "answer_field": form.get("answer_field", "answer"),
                    "system_prompt": form.get("system_prompt", "You are an AI assistant."),
                    "template": form.get("template", "<|system|>\n{system_prompt}\n</s>\n<|user|>\n{question}\n</s>\n<|assistant|>\n{answer}\n</s>"),
                    "validation_split": float(form.get("validation_split", 0.2)),
                    "seed": int(form.get("seed", 42)),
                    "max_length": int(form.get("max_length", 512)),
                },
                "model": {
                    "pretrained_model_name": form.get("pretrained_model_name", "TinyLlama/TinyLlama-1.1B-Chat-v1.0"),
                    "trust_remote_code": "trust_remote_code" in form,
                    "pad_token_override": form.get("pad_token_override") or None,
                },
                "peft": {
                    "enabled": "peft_enabled" in form,
                    "r": int(form.get("peft_r", 8)),
                    "lora_alpha": int(form.get("peft_lora_alpha", 16)),
                    "lora_dropout": float(form.get("peft_lora_dropout", 0.05)),
                    "bias": form.get("peft_bias", "none"),
                    "target_modules": target_modules or ["q_proj", "k_proj", "v_proj", "o_proj"],
                },
                "training": {
                    "num_train_epochs": float(form.get("num_train_epochs", 3)),
                    "per_device_train_batch_size": int(form.get("per_device_train_batch_size", 1)),
                    "per_device_eval_batch_size": int(form.get("per_device_eval_batch_size", 1)),
                    "learning_rate": float(form.get("learning_rate", 2e-5)),
                    "weight_decay": float(form.get("weight_decay", 0.0)),
                    "warmup_ratio": float(form.get("warmup_ratio", 0.03)),
                    "gradient_accumulation_steps": int(form.get("gradient_accumulation_steps", 8)),
                    "lr_scheduler_type": form.get("lr_scheduler_type", "cosine"),
                    "logging_steps": int(form.get("logging_steps", 5)),
                    "eval_steps": int(form.get("eval_steps", 20)),
                    "save_steps": int(form.get("save_steps", 100)),
                    "save_total_limit": int(form.get("save_total_limit", 2)),
                    "max_steps": int(form.get("max_steps", -1)),
                    "gradient_checkpointing": "gradient_checkpointing" in form,
                    "fp16": "fp16" in form,
                    "bf16": "bf16" in form,
                    "early_stopping_patience": int(form.get("early_stopping_patience")) if form.get("early_stopping_patience") else None,
                    "early_stopping_metric": form.get("early_stopping_metric", "eval_loss"),
                    "early_stopping_greater_is_better": "early_stopping_greater_is_better" in form,
                    "auto_evaluate": "auto_evaluate" in form,
                },
            },
        }
    resp = requests.post(f"{API_BASE_URL}/experiments/causal-lm", json=payload, timeout=10)
    if resp.status_code == 200:
        experiment_id = resp.json().get("experiment_id")
        if experiment_id:
            return redirect(url_for("experiment_detail", experiment_id=experiment_id))
    return redirect(url_for("experiments_page"))


@app.route("/experiments")
def experiments_page():
    resp = requests.get(f"{API_BASE_URL}/experiments", timeout=10)
    data = resp.json()
    return render_template_string(EXPERIMENTS_TEMPLATE, experiments=data.get("experiments", []))


@app.route("/experiments/compare")
def experiments_compare_page():
    ids = request.args.get("ids", "")
    experiment_ids = [eid.strip() for eid in ids.split(",") if eid.strip()]
    if len(experiment_ids) < 2:
        return redirect(url_for("evaluations_compare_page"))

    resp = requests.post(
        f"{API_BASE_URL}/experiments/compare",
        json=experiment_ids,
        timeout=30,
    )
    if resp.status_code != 200:
        return redirect(url_for("evaluations_compare_page"))

    data = resp.json()
    return render_template_string(
        EXPERIMENTS_COMPARE_TEMPLATE,
        experiments=data.get("experiments", []),
        config_diff=data.get("config_diff", {}),
    )


@app.route("/experiments/<experiment_id>")
def experiment_detail(experiment_id: str):
    resp = requests.get(f"{API_BASE_URL}/experiments/{experiment_id}", timeout=10)
    if resp.status_code != 200:
        return redirect(url_for("experiments_page"))
    logs_resp = requests.get(f"{API_BASE_URL}/experiments/{experiment_id}/logs", timeout=10)
    logs = logs_resp.json().get("logs", []) if logs_resp.status_code == 200 else []
    benchmarks_resp = requests.get(f"{API_BASE_URL}/benchmarks", timeout=10)
    benchmarks = benchmarks_resp.json().get("benchmarks", []) if benchmarks_resp.status_code == 200 else []
    return render_template_string(EXPERIMENT_DETAIL_TEMPLATE, experiment=resp.json(), logs=logs, benchmarks=benchmarks)


@app.route("/experiments/<experiment_id>/copy")
def copy_experiment(experiment_id: str):
    exp_resp = requests.get(f"{API_BASE_URL}/experiments/{experiment_id}", timeout=10)
    if exp_resp.status_code != 200:
        return redirect(url_for("experiments_page"))
    experiment = exp_resp.json()
    dataset_resp = requests.get(f"{API_BASE_URL}/datasets/{experiment['dataset_id']}", timeout=10)
    if dataset_resp.status_code != 200:
        return redirect(url_for("experiment_detail", experiment_id=experiment_id))
    return render_template_string(
        COPY_EXPERIMENT_TEMPLATE,
        source_experiment=experiment,
        dataset=dataset_resp.json(),
        cfg=experiment["config"],
    )


@app.route("/experiments/<experiment_id>/delete", methods=["POST"])
def delete_experiment(experiment_id: str):
    requests.delete(f"{API_BASE_URL}/experiments/{experiment_id}", timeout=10)
    return redirect(url_for("experiments_page"))


@app.route("/experiments/<experiment_id>/stop", methods=["POST"])
def stop_experiment(experiment_id: str):
    resp = requests.post(f"{API_BASE_URL}/experiments/{experiment_id}/stop", timeout=10)
    if request.headers.get("Accept") == "application/json" or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return resp.json()
    return redirect(url_for("experiment_detail", experiment_id=experiment_id))


@app.route("/api/health")
def api_health():
    resp = requests.get(f"{API_BASE_URL}/health", timeout=5)
    return jsonify(resp.json())


@app.route("/api/configs/<config_name>")
def api_get_config(config_name: str):
    resp = requests.get(f"{API_BASE_URL}/configs/{config_name}", timeout=10)
    return jsonify(resp.json())


@app.route("/api/experiments/<experiment_id>")
def api_get_experiment(experiment_id: str):
    resp = requests.get(f"{API_BASE_URL}/experiments/{experiment_id}", timeout=10)
    return jsonify(resp.json())


@app.route("/api/experiments/<experiment_id>/logs")
def api_get_experiment_logs(experiment_id: str):
    resp = requests.get(f"{API_BASE_URL}/experiments/{experiment_id}/logs", timeout=10)
    return jsonify(resp.json())


@app.route("/api/evaluations/<eval_id>")
def api_get_evaluation(eval_id: str):
    resp = requests.get(f"{API_BASE_URL}/evaluations/{eval_id}", timeout=10)
    return jsonify(resp.json())


# --- Benchmark Routes ---


@app.route("/benchmarks")
def benchmarks_page():
    resp = requests.get(f"{API_BASE_URL}/benchmarks", timeout=10)
    data = resp.json()
    return render_template_string(BENCHMARKS_TEMPLATE, benchmarks=data.get("benchmarks", []))


@app.route("/benchmarks/create", methods=["POST"])
def create_benchmark():
    form = request.form.to_dict()
    payload = {
        "name": form.get("name"),
        "question": form.get("question"),
        "gold_answer": form.get("gold_answer"),
    }
    requests.post(f"{API_BASE_URL}/benchmarks", json=payload, timeout=10)
    return redirect(url_for("benchmarks_page"))


@app.route("/benchmarks/<benchmark_id>/delete", methods=["POST"])
def delete_benchmark(benchmark_id: str):
    requests.delete(f"{API_BASE_URL}/benchmarks/{benchmark_id}", timeout=10)
    return redirect(url_for("benchmarks_page"))


@app.route("/benchmarks/<benchmark_id>/evaluate", methods=["GET"])
def benchmark_evaluate_form(benchmark_id: str):
    benchmark_resp = requests.get(f"{API_BASE_URL}/benchmarks/{benchmark_id}", timeout=10)
    if benchmark_resp.status_code != 200:
        return redirect(url_for("benchmarks_page"))
    experiments_resp = requests.get(f"{API_BASE_URL}/experiments", timeout=10)
    experiments = experiments_resp.json().get("experiments", [])
    return render_template_string(
        BENCHMARK_EVALUATE_TEMPLATE,
        benchmark=benchmark_resp.json(),
        experiments=experiments,
    )


@app.route("/benchmarks/<benchmark_id>/evaluate", methods=["POST"])
def start_benchmark_eval(benchmark_id: str):
    form = request.form.to_dict()
    payload = {
        "experiment_id": form.get("experiment_id"),
        "max_new_tokens": int(form.get("max_new_tokens", 128)),
        "temperature": float(form.get("temperature", 0.7)),
        "top_p": float(form.get("top_p", 0.9)),
    }
    resp = requests.post(f"{API_BASE_URL}/benchmarks/{benchmark_id}/evaluate", json=payload, timeout=600)
    
    # Return JSON for AJAX requests so frontend can poll for completion
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        data = resp.json()
        data["benchmark_id"] = benchmark_id
        return jsonify(data)
    
    return redirect(url_for("benchmark_results", benchmark_id=benchmark_id))


@app.route("/benchmarks/<benchmark_id>/results")
def benchmark_results(benchmark_id: str):
    benchmark_resp = requests.get(f"{API_BASE_URL}/benchmarks/{benchmark_id}", timeout=10)
    if benchmark_resp.status_code != 200:
        return redirect(url_for("benchmarks_page"))
    evals_resp = requests.get(f"{API_BASE_URL}/benchmarks/{benchmark_id}/evaluations", timeout=10)
    return render_template_string(
        BENCHMARK_RESULTS_TEMPLATE,
        benchmark=benchmark_resp.json(),
        evaluations=evals_resp.json().get("evaluations", []),
    )


@app.route("/evaluations/<eval_id>")
def evaluation_detail(eval_id: str):
    resp = requests.get(f"{API_BASE_URL}/evaluations/{eval_id}", timeout=10)
    if resp.status_code != 200:
        return redirect(url_for("benchmarks_page"))
    return render_template_string(EVALUATION_DETAIL_TEMPLATE, evaluation=resp.json())


@app.route("/evaluations")
def evaluations_compare_page():
    resp = requests.get(f"{API_BASE_URL}/evaluations/compare", timeout=10)
    data = resp.json() if resp.status_code == 200 else {"evaluations": []}
    return render_template_string(EVALUATIONS_COMPARE_TEMPLATE, evaluations=data.get("evaluations", []))


@app.route("/evaluations/<eval_id>/delete", methods=["POST"])
def delete_evaluation(eval_id: str):
    requests.delete(f"{API_BASE_URL}/evaluations/{eval_id}", timeout=10)
    return redirect(url_for("evaluations_compare_page"))


# --- Meta-Learning Routes ---


@app.route("/meta")
def meta_page():
    features_resp = requests.get(f"{API_BASE_URL}/meta/features", timeout=10)
    features = features_resp.json().get("features", []) if features_resp.status_code == 200 else []
    
    # Count synthetic vs real
    synthetic_count = sum(1 for f in features if f.get("is_synthetic"))
    real_count = len(features) - synthetic_count
    
    # Check if predictor is trained by trying to get feature importance
    importance = []
    predictor_trained = False
    try:
        importance_resp = requests.get(f"{API_BASE_URL}/meta/feature-importance", timeout=10)
        if importance_resp.status_code == 200:
            predictor_trained = True
            importance_data = importance_resp.json()
            importance = sorted(importance_data.items(), key=lambda x: x[1], reverse=True)
    except Exception:
        pass
    
    # Check if we can train (need 5+ features with ROUGE scores)
    can_train = len([f for f in features if f.get("final_bleu_score")]) >= 5
    
    return render_template_string(
        META_FEATURES_TEMPLATE,
        features=features,
        importance=importance,
        predictor_trained=predictor_trained,
        can_train=can_train,
        synthetic_count=synthetic_count,
        real_count=real_count,
    )


@app.route("/meta/probe")
def meta_probe_page():
    dataset_id = request.args.get("dataset_id")
    if not dataset_id:
        return redirect(url_for("datasets_page"))
    resp = requests.get(f"{API_BASE_URL}/datasets/{dataset_id}", timeout=10)
    if resp.status_code != 200:
        return redirect(url_for("datasets_page"))
    configs_resp = requests.get(f"{API_BASE_URL}/configs/by-type/causal_lm", timeout=10)
    configs = configs_resp.json().get("configs", []) if configs_resp.status_code == 200 else []
    return render_template_string(META_PROBE_TEMPLATE, dataset=resp.json(), configs=configs)


@app.route("/meta/probe", methods=["POST"])
def run_meta_probe():
    form = request.form.to_dict()
    
    payload = {
        "dataset_id": form.get("dataset_id"),
        "probe_steps": int(form.get("probe_steps", 10)),
        "config": {
            "data": {
                "question_field": form.get("question_field", "question"),
                "answer_field": form.get("answer_field", "answer"),
                "system_prompt": form.get("system_prompt", "You are an AI assistant."),
                "template": form.get("template", "<|system|>\n{system_prompt}\n</s>\n<|user|>\n{question}\n</s>\n<|assistant|>\n{answer}\n</s>"),
                "validation_split": 0.2,
                "seed": 42,
                "max_length": int(form.get("max_length", 512)),
            },
            "model": {
                "pretrained_model_name": form.get("pretrained_model_name", "TinyLlama/TinyLlama-1.1B-Chat-v1.0"),
                "trust_remote_code": False,
                "pad_token_override": form.get("pad_token_override") or None,
            },
            "peft": {
                "enabled": "peft_enabled" in form,
                "r": int(form.get("peft_r", 8)),
                "lora_alpha": int(form.get("peft_lora_alpha", 16)),
                "lora_dropout": 0.05,
                "bias": "none",
                "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
            },
            "training": {
                "num_train_epochs": 1,
                "per_device_train_batch_size": int(form.get("per_device_train_batch_size", 1)),
                "per_device_eval_batch_size": 1,
                "learning_rate": float(form.get("learning_rate", 2e-5)),
                "weight_decay": 0.0,
                "warmup_ratio": float(form.get("warmup_ratio", 0.03)),
                "logging_steps": 1,
                "eval_steps": 50,
                "save_steps": 200,
                "save_total_limit": 1,
                "gradient_accumulation_steps": int(form.get("gradient_accumulation_steps", 4)),
                "max_steps": -1,
                "lr_scheduler_type": "cosine",
                "gradient_checkpointing": True,
                "bf16": False,
                "fp16": True,
            },
        },
    }
    
    resp = requests.post(f"{API_BASE_URL}/meta/probe", json=payload, timeout=3600)
    
    if resp.status_code != 200:
        return redirect(url_for("meta_page"))
    
    data = resp.json()
    features = data.get("features", {})
    
    # Try to get prediction if predictor is trained
    prediction = None
    try:
        importance_resp = requests.get(f"{API_BASE_URL}/meta/feature-importance", timeout=10)
        if importance_resp.status_code == 200:
            # Predictor is trained, make prediction
            predict_resp = requests.post(f"{API_BASE_URL}/meta/predict", json=payload, timeout=3600)
            if predict_resp.status_code == 200:
                prediction = predict_resp.json().get("predicted_performance")
    except Exception:
        pass
    
    return render_template_string(META_PROBE_RESULT_TEMPLATE, features=features, prediction=prediction)


@app.route("/meta/train", methods=["POST"])
def train_meta_predictor():
    requests.post(f"{API_BASE_URL}/meta/train-predictor", json={"target": "final_bleu_score"}, timeout=120)
    return redirect(url_for("meta_page"))


@app.route("/meta/generate-synthetic", methods=["POST"])
def generate_synthetic():
    """Generate synthetic meta-features for predictor bootstrapping."""
    requests.post(f"{API_BASE_URL}/meta/generate-synthetic", json={"n_samples": 100, "seed": 42}, timeout=30)
    return redirect(url_for("meta_page"))


@app.route("/meta/clear-synthetic", methods=["POST"])
def clear_synthetic():
    """Remove all synthetic meta-features."""
    requests.delete(f"{API_BASE_URL}/meta/synthetic", timeout=30)
    return redirect(url_for("meta_page"))


@app.route("/meta/explain/<experiment_id>")
def meta_explain(experiment_id: str):
    resp = requests.get(f"{API_BASE_URL}/meta/explain/{experiment_id}", timeout=30)
    if resp.status_code != 200:
        return redirect(url_for("meta_page"))
    
    data = resp.json()
    shap_values = data.get("shap_values", {})
    max_shap = max(abs(v) for v in shap_values.values()) if shap_values else 1
    
    return render_template_string(
        META_EXPLAIN_TEMPLATE,
        experiment_id=experiment_id,
        prediction=data.get("prediction", 0),
        top_drivers=data.get("top_drivers", []),
        shap_values=shap_values,
        max_shap=max_shap,
    )


@app.route("/experiments/<experiment_id>/extract-meta", methods=["POST"])
def extract_experiment_meta(experiment_id: str):
    """Extract meta-features from a completed experiment."""
    requests.post(f"{API_BASE_URL}/meta/extract/{experiment_id}", timeout=1200)
    return redirect(url_for("meta_page"))


@app.route("/meta/optimize")
def meta_optimize_page():
    """Config optimizer page."""
    dataset_id = request.args.get("dataset_id")
    if not dataset_id:
        return redirect(url_for("datasets_page"))
    
    resp = requests.get(f"{API_BASE_URL}/datasets/{dataset_id}", timeout=10)
    if resp.status_code != 200:
        return redirect(url_for("datasets_page"))
    
    return render_template_string(META_OPTIMIZE_TEMPLATE, dataset=resp.json())


@app.route("/meta/optimize", methods=["POST"])
def run_meta_optimize():
    """Start config optimization job."""
    form = request.form.to_dict()
    
    # Parse search space from form
    def parse_floats(s):
        return [float(x.strip()) for x in s.split(",") if x.strip()]
    
    def parse_ints(s):
        return [int(x.strip()) for x in s.split(",") if x.strip()]
    
    search_space = {
        "learning_rates": parse_floats(form.get("learning_rates", "1e-5, 2e-5, 5e-5, 1e-4")),
        "lora_r_values": parse_ints(form.get("lora_r_values", "4, 8, 16")),
        "batch_sizes": parse_ints(form.get("batch_sizes", "1, 2")),
        "num_epochs": parse_ints(form.get("num_epochs", "1, 2, 3")),
    }
    
    payload = {
        "dataset_id": form.get("dataset_id"),
        "probe_steps": int(form.get("probe_steps", 10)),
        "max_candidates": int(form.get("max_candidates", 12)),
        "search_space": search_space,
        "config": {
            "data": {
                "question_field": form.get("question_field", "question"),
                "answer_field": form.get("answer_field", "answer"),
                "system_prompt": "You are a helpful AI assistant.",
                "template": "<|system|>\n{system_prompt}\n</s>\n<|user|>\n{question}\n</s>\n<|assistant|>\n{answer}\n</s>",
                "validation_split": 0.2,
                "seed": 42,
                "max_length": int(form.get("max_length", 512)),
            },
            "model": {
                "pretrained_model_name": form.get("pretrained_model_name", "TinyLlama/TinyLlama-1.1B-Chat-v1.0"),
                "trust_remote_code": False,
                "pad_token_override": "</s>",
            },
            "peft": {
                "enabled": True,
                "r": 8,
                "lora_alpha": 16,
                "lora_dropout": 0.05,
                "bias": "none",
                "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
            },
            "training": {
                "num_train_epochs": 1,
                "per_device_train_batch_size": 1,
                "per_device_eval_batch_size": 1,
                "learning_rate": 2e-5,
                "weight_decay": 0.0,
                "warmup_ratio": 0.03,
                "logging_steps": 1,
                "eval_steps": 50,
                "save_steps": 200,
                "save_total_limit": 1,
                "gradient_accumulation_steps": 4,
                "max_steps": -1,
                "lr_scheduler_type": "cosine",
                "gradient_checkpointing": True,
                "bf16": False,
                "fp16": True,
            },
        },
    }
    
    # Start the job (returns immediately with job_id)
    resp = requests.post(f"{API_BASE_URL}/meta/optimize", json=payload, timeout=30)
    
    if resp.status_code != 200:
        return redirect(url_for("meta_page"))
    
    data = resp.json()
    job_id = data.get("job_id")
    
    # Redirect to progress page
    return redirect(url_for("optimize_progress", job_id=job_id))


@app.route("/meta/optimize/<job_id>")
def optimize_progress(job_id: str):
    """Show optimization progress page."""
    resp = requests.get(f"{API_BASE_URL}/meta/optimize/{job_id}", timeout=10)
    
    if resp.status_code != 200:
        return redirect(url_for("meta_page"))
    
    data = resp.json()
    
    # If completed or failed, redirect to results
    if data.get("status") in ["completed", "failed"]:
        return redirect(url_for("optimize_results", job_id=job_id))
    
    return render_template_string(
        META_OPTIMIZE_PROGRESS_TEMPLATE,
        job_id=job_id,
        status=data.get("status", "unknown"),
        started_at=data.get("started_at", ""),
    )


@app.route("/meta/optimize/<job_id>/results")
def optimize_results(job_id: str):
    """Show optimization results."""
    resp = requests.get(f"{API_BASE_URL}/meta/optimize/{job_id}", timeout=10)
    
    if resp.status_code != 200:
        return redirect(url_for("meta_page"))
    
    data = resp.json()
    
    # If still running, redirect to progress
    if data.get("status") not in ["completed", "failed"]:
        return redirect(url_for("optimize_progress", job_id=job_id))
    
    # Handle failed jobs
    if data.get("status") == "failed":
        return render_template_string(
            META_OPTIMIZE_RESULTS_TEMPLATE,
            candidates=[],
            best_config={},
            message=f"Optimization failed: {data.get('error', 'Unknown error')}",
        )
    
    return render_template_string(
        META_OPTIMIZE_RESULTS_TEMPLATE,
        candidates=data.get("candidates", []),
        best_config=data.get("best_config", {}),
        message=data.get("message", ""),
    )


@app.route("/api/optimize/<job_id>/status")
def optimize_status_api(job_id: str):
    """AJAX endpoint for optimization status polling."""
    resp = requests.get(f"{API_BASE_URL}/meta/optimize/{job_id}", timeout=10)
    
    if resp.status_code != 200:
        return {"status": "error", "error": "Job not found"}, 404
    
    data = resp.json()
    return {"status": data.get("status", "unknown")}


# --- AutoTune API Routes ---


@app.route("/api/autotune/run", methods=["POST"])
def api_autotune_run():
    """Start an autotune job."""
    data = request.get_json()
    resp = requests.post(f"{API_BASE_URL}/autotune/run", json=data, timeout=30)
    return jsonify(resp.json()), resp.status_code


@app.route("/api/autotune/<job_id>")
def api_autotune_status(job_id: str):
    """Get autotune job status."""
    resp = requests.get(f"{API_BASE_URL}/autotune/{job_id}", timeout=10)
    return jsonify(resp.json()), resp.status_code


@app.route("/api/autotune")
def api_autotune_list():
    """List all autotune jobs."""
    resp = requests.get(f"{API_BASE_URL}/autotune", timeout=10)
    return jsonify(resp.json()), resp.status_code


@app.route("/api/datasets/<dataset_id>/row/<int:row_idx>")
def api_dataset_row(dataset_id: str, row_idx: int):
    """Get a specific row from a dataset."""
    import pandas as pd
    resp = requests.get(f"{API_BASE_URL}/datasets/{dataset_id}", timeout=10)
    if resp.status_code != 200:
        return jsonify({"error": "Dataset not found"}), 404
    dataset = resp.json()
    try:
        df = pd.read_csv(dataset["path"])
        if row_idx >= len(df):
            return jsonify({"error": f"Row {row_idx} out of range (max: {len(df)-1})"}), 400
        row = df.iloc[row_idx].to_dict()
        return jsonify({"row": row, "row_count": len(df)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001, debug=True)

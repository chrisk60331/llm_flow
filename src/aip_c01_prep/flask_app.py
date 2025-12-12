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
                @apply bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden;
            }
            .card-header {
                @apply px-6 py-4 border-b border-gray-100 bg-gray-50/50;
            }
            .card-body {
                @apply p-6;
            }
            .form-group {
                @apply space-y-1.5;
            }
            .form-label {
                @apply block text-sm font-medium text-gray-700;
            }
            .form-input {
                @apply w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all duration-200 bg-white;
            }
            .form-textarea {
                @apply w-full px-3 py-2 rounded-lg border border-gray-300 text-sm font-mono focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all duration-200 bg-white resize-none;
            }
            .form-select {
                @apply w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all duration-200 bg-white;
            }
            .form-checkbox {
                @apply w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 transition-all duration-200;
            }
            .section-card {
                @apply bg-white rounded-xl border border-gray-200 overflow-hidden;
            }
            .section-header {
                @apply px-5 py-3 bg-gradient-to-r from-gray-50 to-white border-b border-gray-200 flex items-center gap-2;
            }
            .section-title {
                @apply text-base font-semibold text-gray-800;
            }
            .section-body {
                @apply p-5;
            }
            .badge {
                @apply px-2.5 py-1 text-xs font-medium rounded-full;
            }
            .badge-blue {
                @apply bg-blue-100 text-blue-700;
            }
            .badge-green {
                @apply bg-emerald-100 text-emerald-700;
            }
            .badge-red {
                @apply bg-red-100 text-red-700;
            }
            .badge-gray {
                @apply bg-gray-100 text-gray-700;
            }
            .metric-card {
                @apply bg-gradient-to-br from-gray-50 to-white p-4 rounded-xl border border-gray-100;
            }
            .metric-value {
                @apply text-2xl font-bold text-primary-600;
            }
            .metric-label {
                @apply text-xs font-medium text-gray-500 uppercase tracking-wide;
            }
        }
    </style>
</head>
<body class="bg-gradient-to-br from-gray-50 to-gray-100 min-h-screen">
    <nav class="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex items-center justify-between h-16">
                <a href="/" class="flex items-center gap-2">
                    <div class="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center">
                        <span class="text-white font-bold text-sm">AI</span>
                    </div>
                    <span class="text-lg font-semibold text-gray-900">AIP-C01 Prep</span>
                </a>
                <div class="flex items-center gap-1">
                    <a href="/" class="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all">Home</a>
                    <a href="/datasets" class="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all">Datasets</a>
                    <a href="/configs" class="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all">Configs</a>
                    <a href="/experiments" class="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all">Experiments</a>
                    <a href="/benchmarks" class="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all">Benchmarks</a>
                    <a href="/evaluations" class="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all">Evaluations</a>
                </div>
            </div>
        </div>
    </nav>
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {% block content %}{% endblock %}
    </main>
</body>
</html>
"""

HOME_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Home - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="max-w-4xl mx-auto">
            <div class="text-center mb-10">
                <h1 class="text-4xl font-bold text-gray-900 mb-3">ML Experiment Platform</h1>
                <p class="text-lg text-gray-600">Fine-tune language models with ease</p>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <a href="/datasets" class="card group hover:shadow-lg hover:border-primary-200 transition-all duration-300">
                    <div class="card-body text-center py-8">
                        <div class="w-14 h-14 bg-blue-100 rounded-2xl flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform">
                            <svg class="w-7 h-7 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"></path></svg>
                        </div>
                        <h2 class="text-xl font-semibold text-gray-900 mb-2">Datasets</h2>
                        <p class="text-gray-600 text-sm">Upload and manage training data</p>
                    </div>
                </a>
                <a href="/configs" class="card group hover:shadow-lg hover:border-primary-200 transition-all duration-300">
                    <div class="card-body text-center py-8">
                        <div class="w-14 h-14 bg-purple-100 rounded-2xl flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform">
                            <svg class="w-7 h-7 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                        </div>
                        <h2 class="text-xl font-semibold text-gray-900 mb-2">Configs</h2>
                        <p class="text-gray-600 text-sm">View saved configurations</p>
                    </div>
                </a>
                <a href="/experiments" class="card group hover:shadow-lg hover:border-primary-200 transition-all duration-300">
                    <div class="card-body text-center py-8">
                        <div class="w-14 h-14 bg-emerald-100 rounded-2xl flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform">
                            <svg class="w-7 h-7 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path></svg>
                        </div>
                        <h2 class="text-xl font-semibold text-gray-900 mb-2">Experiments</h2>
                        <p class="text-gray-600 text-sm">Run and track ML experiments</p>
                    </div>
                </a>
                <a href="/benchmarks" class="card group hover:shadow-lg hover:border-primary-200 transition-all duration-300">
                    <div class="card-body text-center py-8">
                        <div class="w-14 h-14 bg-amber-100 rounded-2xl flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform">
                            <svg class="w-7 h-7 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
                        </div>
                        <h2 class="text-xl font-semibold text-gray-900 mb-2">Benchmarks</h2>
                        <p class="text-gray-600 text-sm">Evaluate with BLEU scores</p>
                    </div>
                </a>
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
            <h1 class="text-2xl font-bold text-gray-900">Datasets</h1>
            <p class="text-gray-600">Upload and manage your training datasets</p>
        </div>
        
        <div class="card mb-6">
            <div class="card-header">
                <h2 class="font-semibold text-gray-800">Upload New Dataset</h2>
            </div>
            <div class="card-body">
                <form action="/datasets/upload" method="post" enctype="multipart/form-data" class="flex items-center gap-4">
                    <div class="flex-1">
                        <input type="file" name="file" accept=".csv" required
                            class="block w-full text-sm text-gray-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100 file:cursor-pointer cursor-pointer">
                    </div>
                    <button type="submit" class="btn-primary">Upload CSV</button>
                </form>
            </div>
        </div>
        
        <div class="card">
            <div class="overflow-x-auto">
                <table class="w-full">
                    <thead>
                        <tr class="bg-gray-50 border-b border-gray-200">
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Filename</th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Columns</th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Rows</th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Uploaded</th>
                            <th class="px-6 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Actions</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        {% for dataset in datasets %}
                        <tr class="hover:bg-gray-50 transition-colors">
                            <td class="px-6 py-4">
                                <span class="font-medium text-gray-900">{{ dataset.filename }}</span>
                            </td>
                            <td class="px-6 py-4">
                                <span class="text-sm text-gray-600">{{ dataset.columns | join(', ') | truncate(40) }}</span>
                            </td>
                            <td class="px-6 py-4">
                                <span class="badge badge-blue">{{ dataset.row_count }} rows</span>
                            </td>
                            <td class="px-6 py-4 text-sm text-gray-500">{{ dataset.uploaded_at[:10] }}</td>
                            <td class="px-6 py-4">
                                <div class="flex items-center justify-end gap-2">
                                    <a href="/experiments/new/masked-lm?dataset_id={{ dataset.id }}" class="text-sm font-medium text-blue-600 hover:text-blue-800">MLM</a>
                                    <span class="text-gray-300">|</span>
                                    <a href="/experiments/new/causal-lm?dataset_id={{ dataset.id }}" class="text-sm font-medium text-emerald-600 hover:text-emerald-800">Causal</a>
                                    <span class="text-gray-300">|</span>
                                    <form action="/datasets/{{ dataset.id }}/delete" method="post" class="inline">
                                        <button type="submit" class="text-sm font-medium text-red-500 hover:text-red-700">Delete</button>
                                    </form>
                                </div>
                            </td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="5" class="px-6 py-12 text-center text-gray-500">
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
        <div class="mb-6">
            <h1 class="text-2xl font-bold text-gray-900">Saved Configurations</h1>
            <p class="text-gray-600">YAML config files from configs/</p>
        </div>
        
        <div class="card">
            <div class="overflow-x-auto">
                <table class="w-full">
                    <thead>
                        <tr class="bg-gray-50 border-b border-gray-200">
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Name</th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Type</th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Model</th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Dataset</th>
                            <th class="px-6 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Actions</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        {% for config in configs %}
                        <tr class="hover:bg-gray-50 transition-colors">
                            <td class="px-6 py-4 font-medium text-gray-900">{{ config.name }}</td>
                            <td class="px-6 py-4">
                                {% if config.experiment_type == 'causal_lm' %}
                                <span class="badge badge-green">Causal LM</span>
                                {% else %}
                                <span class="badge badge-blue">Masked LM</span>
                                {% endif %}
                            </td>
                            <td class="px-6 py-4 text-sm text-gray-600 font-mono">{{ config.model_name | truncate(35) }}</td>
                            <td class="px-6 py-4 text-sm text-gray-500">{{ config.dataset_path }}</td>
                            <td class="px-6 py-4 text-right">
                                <a href="/configs/{{ config.name }}" class="text-sm font-medium text-primary-600 hover:text-primary-800">View YAML</a>
                            </td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="5" class="px-6 py-12 text-center text-gray-500">No saved configurations</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endblock %}""",
    )
)

CONFIG_DETAIL_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Config - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="flex items-center justify-between mb-6">
            <div>
                <h1 class="text-2xl font-bold text-gray-900">{{ config_name }}.yaml</h1>
                <p class="text-gray-600">Configuration file contents</p>
            </div>
            <a href="/configs" class="text-sm font-medium text-gray-600 hover:text-gray-900">&larr; Back to Configs</a>
        </div>
        
        <div class="card">
            <div class="card-body">
                <pre class="bg-gray-900 text-gray-100 p-6 rounded-lg overflow-x-auto text-sm font-mono leading-relaxed">{{ config_yaml }}</pre>
            </div>
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
                    <h1 class="text-2xl font-bold text-gray-900">New Experiment</h1>
                </div>
                <p class="text-gray-600">
                    Dataset: <span class="font-medium text-gray-900">{{ dataset.filename }}</span> 
                    <span class="text-gray-400">•</span> {{ dataset.row_count }} rows 
                    <span class="text-gray-400">•</span> Columns: {{ dataset.columns | join(', ') }}
                </p>
            </div>
            
            <form action="/experiments/masked-lm" method="post" class="space-y-6" id="experiment-form">
                <input type="hidden" name="dataset_id" value="{{ dataset.id }}">
                
                <!-- Config Selector -->
                {% if configs %}
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                        <h2 class="section-title">Load Existing Config</h2>
                    </div>
                    <div class="section-body">
                        <div class="flex items-center gap-4">
                            <div class="form-group flex-1">
                                <label class="form-label">Select a saved configuration</label>
                                <select id="config-selector" class="form-select">
                                    <option value="">-- Use defaults --</option>
                                    {% for config in configs %}
                                    <option value="{{ config.name }}">{{ config.name }} ({{ config.model_name }})</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <button type="button" id="load-config-btn" class="btn-primary mt-5">Load Config</button>
                        </div>
                        <p class="text-xs text-gray-500 mt-2">Loading a config will populate the form fields below. You can still edit values before starting.</p>
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
                                <label class="form-label">Text Fields <span class="text-gray-400 font-normal">(comma-separated)</span></label>
                                <input type="text" name="text_fields" value="question,answer" class="form-input" placeholder="question,answer">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Separator</label>
                                <input type="text" name="separator" value="\\n\\n" class="form-input font-mono">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Validation Split</label>
                                <input type="number" name="validation_split" value="0.2" step="0.05" min="0.05" max="0.5" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Random Seed</label>
                                <input type="number" name="seed" value="42" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Max Token Length</label>
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
                                <label class="form-label">Pretrained Model</label>
                                <input type="text" name="pretrained_model_name" value="distilbert-base-uncased" class="form-input font-mono">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Freeze Encoder Layers <span class="text-gray-400 font-normal">(0-6)</span></label>
                                <input type="number" name="freeze_encoder_layers" value="0" min="0" max="6" class="form-input">
                            </div>
                            <div class="form-group flex items-center gap-3 pt-2">
                                <input type="checkbox" name="freeze_embedding" id="freeze_embedding" class="form-checkbox">
                                <label for="freeze_embedding" class="text-sm text-gray-700">Freeze Embedding Layer</label>
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
                                <label class="form-label">Epochs</label>
                                <input type="number" name="num_train_epochs" value="3" step="0.5" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Learning Rate</label>
                                <input type="text" name="learning_rate" value="5e-5" class="form-input font-mono">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Train Batch Size</label>
                                <input type="number" name="per_device_train_batch_size" value="8" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Eval Batch Size</label>
                                <input type="number" name="per_device_eval_batch_size" value="8" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Weight Decay</label>
                                <input type="number" name="weight_decay" value="0.01" step="0.01" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Warmup Ratio</label>
                                <input type="number" name="warmup_ratio" value="0.0" step="0.01" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Gradient Accum Steps</label>
                                <input type="number" name="gradient_accumulation_steps" value="1" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Max Steps <span class="text-gray-400 font-normal">(-1 = off)</span></label>
                                <input type="number" name="max_steps" value="-1" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Logging Steps</label>
                                <input type="number" name="logging_steps" value="10" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Eval Steps</label>
                                <input type="number" name="eval_steps" value="50" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Save Steps</label>
                                <input type="number" name="save_steps" value="200" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Save Total Limit</label>
                                <input type="number" name="save_total_limit" value="2" class="form-input">
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="flex justify-end gap-3">
                    <a href="/datasets" class="px-4 py-2 text-gray-700 font-medium hover:bg-gray-100 rounded-lg transition-all">Cancel</a>
                    <button type="submit" class="btn-primary px-8">Start Training</button>
                </div>
            </form>
        </div>
        
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            const loadBtn = document.getElementById('load-config-btn');
            const selector = document.getElementById('config-selector');
            if (!loadBtn || !selector) return;
            
            loadBtn.addEventListener('click', async function() {
                const configName = selector.value;
                if (!configName) return;
                
                loadBtn.disabled = true;
                loadBtn.textContent = 'Loading...';
                
                try {
                    const resp = await fetch('/api/configs/' + configName);
                    const cfg = await resp.json();
                    
                    // Data config
                    if (cfg.data) {
                        if (cfg.data.text_fields) {
                            const tf = Array.isArray(cfg.data.text_fields) ? cfg.data.text_fields.join(',') : cfg.data.text_fields;
                            document.querySelector('[name="text_fields"]').value = tf;
                        }
                        if (cfg.data.separator !== undefined) {
                            document.querySelector('[name="separator"]').value = cfg.data.separator.replace(/\\n/g, '\\\\n');
                        }
                        if (cfg.data.validation_split !== undefined) document.querySelector('[name="validation_split"]').value = cfg.data.validation_split;
                        if (cfg.data.seed !== undefined) document.querySelector('[name="seed"]').value = cfg.data.seed;
                        if (cfg.data.max_length !== undefined) document.querySelector('[name="max_length"]').value = cfg.data.max_length;
                    }
                    
                    // Model config
                    if (cfg.model) {
                        if (cfg.model.pretrained_model_name) document.querySelector('[name="pretrained_model_name"]').value = cfg.model.pretrained_model_name;
                        if (cfg.model.freeze_encoder_layers !== undefined) document.querySelector('[name="freeze_encoder_layers"]').value = cfg.model.freeze_encoder_layers;
                        document.querySelector('[name="freeze_embedding"]').checked = !!cfg.model.freeze_embedding;
                    }
                    
                    // Training config
                    if (cfg.training) {
                        if (cfg.training.num_train_epochs !== undefined) document.querySelector('[name="num_train_epochs"]').value = cfg.training.num_train_epochs;
                        if (cfg.training.learning_rate !== undefined) document.querySelector('[name="learning_rate"]').value = cfg.training.learning_rate;
                        if (cfg.training.per_device_train_batch_size !== undefined) document.querySelector('[name="per_device_train_batch_size"]').value = cfg.training.per_device_train_batch_size;
                        if (cfg.training.per_device_eval_batch_size !== undefined) document.querySelector('[name="per_device_eval_batch_size"]').value = cfg.training.per_device_eval_batch_size;
                        if (cfg.training.weight_decay !== undefined) document.querySelector('[name="weight_decay"]').value = cfg.training.weight_decay;
                        if (cfg.training.warmup_ratio !== undefined) document.querySelector('[name="warmup_ratio"]').value = cfg.training.warmup_ratio;
                        if (cfg.training.gradient_accumulation_steps !== undefined) document.querySelector('[name="gradient_accumulation_steps"]').value = cfg.training.gradient_accumulation_steps;
                        if (cfg.training.max_steps !== undefined) document.querySelector('[name="max_steps"]').value = cfg.training.max_steps;
                        if (cfg.training.logging_steps !== undefined) document.querySelector('[name="logging_steps"]').value = cfg.training.logging_steps;
                        if (cfg.training.eval_steps !== undefined) document.querySelector('[name="eval_steps"]').value = cfg.training.eval_steps;
                        if (cfg.training.save_steps !== undefined) document.querySelector('[name="save_steps"]').value = cfg.training.save_steps;
                        if (cfg.training.save_total_limit !== undefined) document.querySelector('[name="save_total_limit"]').value = cfg.training.save_total_limit;
                    }
                } catch (err) {
                    console.error('Failed to load config:', err);
                    alert('Failed to load config');
                } finally {
                    loadBtn.disabled = false;
                    loadBtn.textContent = 'Load Config';
                }
            });
        });
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
                    <h1 class="text-2xl font-bold text-gray-900">New Experiment</h1>
                </div>
                <p class="text-gray-600">
                    Dataset: <span class="font-medium text-gray-900">{{ dataset.filename }}</span> 
                    <span class="text-gray-400">•</span> {{ dataset.row_count }} rows 
                    <span class="text-gray-400">•</span> Columns: {{ dataset.columns | join(', ') }}
                </p>
            </div>
            
            <form action="/experiments/causal-lm" method="post" class="space-y-6" id="experiment-form">
                <input type="hidden" name="dataset_id" value="{{ dataset.id }}">
                
                <!-- Config Selector -->
                {% if configs %}
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                        <h2 class="section-title">Load Existing Config</h2>
                    </div>
                    <div class="section-body">
                        <div class="flex items-center gap-4">
                            <div class="form-group flex-1">
                                <label class="form-label">Select a saved configuration</label>
                                <select id="config-selector" class="form-select">
                                    <option value="">-- Use defaults --</option>
                                    {% for config in configs %}
                                    <option value="{{ config.name }}">{{ config.name }} ({{ config.model_name }})</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <button type="button" id="load-config-btn" class="btn-primary mt-5">Load Config</button>
                        </div>
                        <p class="text-xs text-gray-500 mt-2">Loading a config will populate the form fields below. You can still edit values before starting.</p>
                    </div>
                </div>
                {% endif %}
                
                <!-- Data Config -->
                <div class="section-card">
                    <div class="section-header">
                        <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"></path></svg>
                        <h2 class="section-title">Data Configuration</h2>
                    </div>
                    <div class="section-body space-y-4">
                        <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
                            <div class="form-group">
                                <label class="form-label">Question Field</label>
                                <input type="text" name="question_field" value="question" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Answer Field</label>
                                <input type="text" name="answer_field" value="answer" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Validation Split</label>
                                <input type="number" name="validation_split" value="0.2" step="0.05" min="0.05" max="0.5" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Random Seed</label>
                                <input type="number" name="seed" value="42" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Max Length</label>
                                <input type="number" name="max_length" value="512" class="form-input">
                            </div>
                        </div>
                        <div class="form-group">
                            <label class="form-label">System Prompt</label>
                            <textarea name="system_prompt" rows="2" class="form-textarea">You are an AI assistant.</textarea>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Chat Template <span class="text-gray-400 font-normal">(use {system_prompt}, {question}, {answer})</span></label>
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
                                <label class="form-label">Pretrained Model</label>
                                <input type="text" name="pretrained_model_name" value="TinyLlama/TinyLlama-1.1B-Chat-v1.0" class="form-input font-mono text-sm">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Pad Token Override</label>
                                <input type="text" name="pad_token_override" value="</s>" class="form-input font-mono">
                            </div>
                            <div class="form-group flex items-center gap-3 pt-2">
                                <input type="checkbox" name="trust_remote_code" id="trust_remote_code" class="form-checkbox">
                                <label for="trust_remote_code" class="text-sm text-gray-700">Trust Remote Code</label>
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
                        <div class="flex items-center gap-3 mb-4 pb-4 border-b border-gray-100">
                            <input type="checkbox" name="peft_enabled" id="peft_enabled" checked class="form-checkbox">
                            <label for="peft_enabled" class="text-sm font-medium text-gray-700">Enable LoRA Adapters</label>
                        </div>
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div class="form-group">
                                <label class="form-label">Rank (r)</label>
                                <input type="number" name="peft_r" value="64" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Alpha</label>
                                <input type="number" name="peft_lora_alpha" value="128" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Dropout</label>
                                <input type="number" name="peft_lora_dropout" value="0.01" step="0.01" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Bias</label>
                                <select name="peft_bias" class="form-select">
                                    <option value="none" selected>none</option>
                                    <option value="lora_only">lora_only</option>
                                    <option value="all">all</option>
                                </select>
                            </div>
                            <div class="form-group md:col-span-4">
                                <label class="form-label">Target Modules <span class="text-gray-400 font-normal">(comma-separated)</span></label>
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
                                <label class="form-label">Epochs</label>
                                <input type="number" name="num_train_epochs" value="3" step="0.5" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Learning Rate</label>
                                <input type="text" name="learning_rate" value="1e-4" class="form-input font-mono">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Train Batch Size</label>
                                <input type="number" name="per_device_train_batch_size" value="1" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Eval Batch Size</label>
                                <input type="number" name="per_device_eval_batch_size" value="1" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Weight Decay</label>
                                <input type="number" name="weight_decay" value="0.0" step="0.01" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Warmup Ratio</label>
                                <input type="number" name="warmup_ratio" value="0.03" step="0.01" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Gradient Accum Steps</label>
                                <input type="number" name="gradient_accumulation_steps" value="8" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">LR Scheduler</label>
                                <select name="lr_scheduler_type" class="form-select">
                                    <option value="cosine" selected>cosine</option>
                                    <option value="linear">linear</option>
                                    <option value="constant">constant</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label class="form-label">Logging Steps</label>
                                <input type="number" name="logging_steps" value="5" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Eval Steps</label>
                                <input type="number" name="eval_steps" value="20" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Save Steps</label>
                                <input type="number" name="save_steps" value="100" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Max Steps <span class="text-gray-400 font-normal">(-1 = off)</span></label>
                                <input type="number" name="max_steps" value="-1" class="form-input">
                            </div>
                        </div>
                        <div class="flex flex-wrap gap-6 mt-4 pt-4 border-t border-gray-100">
                            <label class="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" name="gradient_checkpointing" checked class="form-checkbox">
                                <span class="text-sm text-gray-700">Gradient Checkpointing</span>
                            </label>
                            <label class="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" name="fp16" checked class="form-checkbox">
                                <span class="text-sm text-gray-700">FP16</span>
                            </label>
                            <label class="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" name="bf16" class="form-checkbox">
                                <span class="text-sm text-gray-700">BF16</span>
                            </label>
                        </div>
                    </div>
                </div>
                
                <div class="flex justify-end gap-3">
                    <a href="/datasets" class="px-4 py-2 text-gray-700 font-medium hover:bg-gray-100 rounded-lg transition-all">Cancel</a>
                    <button type="submit" class="btn-success px-8">Start Training</button>
                </div>
            </form>
        </div>
        
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            const loadBtn = document.getElementById('load-config-btn');
            const selector = document.getElementById('config-selector');
            if (!loadBtn || !selector) return;
            
            loadBtn.addEventListener('click', async function() {
                const configName = selector.value;
                if (!configName) return;
                
                loadBtn.disabled = true;
                loadBtn.textContent = 'Loading...';
                
                try {
                    const resp = await fetch('/api/configs/' + configName);
                    const cfg = await resp.json();
                    
                    // Data config
                    if (cfg.data) {
                        if (cfg.data.question_field) document.querySelector('[name="question_field"]').value = cfg.data.question_field;
                        if (cfg.data.answer_field) document.querySelector('[name="answer_field"]').value = cfg.data.answer_field;
                        if (cfg.data.system_prompt) document.querySelector('[name="system_prompt"]').value = cfg.data.system_prompt;
                        if (cfg.data.template) document.querySelector('[name="template"]').value = cfg.data.template;
                        if (cfg.data.validation_split !== undefined) document.querySelector('[name="validation_split"]').value = cfg.data.validation_split;
                        if (cfg.data.seed !== undefined) document.querySelector('[name="seed"]').value = cfg.data.seed;
                        if (cfg.data.max_length !== undefined) document.querySelector('[name="max_length"]').value = cfg.data.max_length;
                    }
                    
                    // Model config
                    if (cfg.model) {
                        if (cfg.model.pretrained_model_name) document.querySelector('[name="pretrained_model_name"]').value = cfg.model.pretrained_model_name;
                        if (cfg.model.pad_token_override) document.querySelector('[name="pad_token_override"]').value = cfg.model.pad_token_override;
                        document.querySelector('[name="trust_remote_code"]').checked = !!cfg.model.trust_remote_code;
                    }
                    
                    // PEFT config
                    if (cfg.peft) {
                        document.querySelector('[name="peft_enabled"]').checked = !!cfg.peft.enabled;
                        if (cfg.peft.r !== undefined) document.querySelector('[name="peft_r"]').value = cfg.peft.r;
                        if (cfg.peft.lora_alpha !== undefined) document.querySelector('[name="peft_lora_alpha"]').value = cfg.peft.lora_alpha;
                        if (cfg.peft.lora_dropout !== undefined) document.querySelector('[name="peft_lora_dropout"]').value = cfg.peft.lora_dropout;
                        if (cfg.peft.bias) document.querySelector('[name="peft_bias"]').value = cfg.peft.bias;
                        if (cfg.peft.target_modules) {
                            const tm = Array.isArray(cfg.peft.target_modules) ? cfg.peft.target_modules.join(',') : cfg.peft.target_modules;
                            document.querySelector('[name="peft_target_modules"]').value = tm;
                        }
                    }
                    
                    // Training config
                    if (cfg.training) {
                        if (cfg.training.num_train_epochs !== undefined) document.querySelector('[name="num_train_epochs"]').value = cfg.training.num_train_epochs;
                        if (cfg.training.learning_rate !== undefined) document.querySelector('[name="learning_rate"]').value = cfg.training.learning_rate;
                        if (cfg.training.per_device_train_batch_size !== undefined) document.querySelector('[name="per_device_train_batch_size"]').value = cfg.training.per_device_train_batch_size;
                        if (cfg.training.per_device_eval_batch_size !== undefined) document.querySelector('[name="per_device_eval_batch_size"]').value = cfg.training.per_device_eval_batch_size;
                        if (cfg.training.weight_decay !== undefined) document.querySelector('[name="weight_decay"]').value = cfg.training.weight_decay;
                        if (cfg.training.warmup_ratio !== undefined) document.querySelector('[name="warmup_ratio"]').value = cfg.training.warmup_ratio;
                        if (cfg.training.gradient_accumulation_steps !== undefined) document.querySelector('[name="gradient_accumulation_steps"]').value = cfg.training.gradient_accumulation_steps;
                        if (cfg.training.lr_scheduler_type) document.querySelector('[name="lr_scheduler_type"]').value = cfg.training.lr_scheduler_type;
                        if (cfg.training.logging_steps !== undefined) document.querySelector('[name="logging_steps"]').value = cfg.training.logging_steps;
                        if (cfg.training.eval_steps !== undefined) document.querySelector('[name="eval_steps"]').value = cfg.training.eval_steps;
                        if (cfg.training.save_steps !== undefined) document.querySelector('[name="save_steps"]').value = cfg.training.save_steps;
                        if (cfg.training.max_steps !== undefined) document.querySelector('[name="max_steps"]').value = cfg.training.max_steps;
                        document.querySelector('[name="gradient_checkpointing"]').checked = !!cfg.training.gradient_checkpointing;
                        document.querySelector('[name="fp16"]').checked = !!cfg.training.fp16;
                        document.querySelector('[name="bf16"]').checked = !!cfg.training.bf16;
                    }
                } catch (err) {
                    console.error('Failed to load config:', err);
                    alert('Failed to load config');
                } finally {
                    loadBtn.disabled = false;
                    loadBtn.textContent = 'Load Config';
                }
            });
        });
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
                    <h1 class="text-2xl font-bold text-gray-900">Copy Experiment</h1>
                </div>
                <p class="text-gray-600">
                    Copying from: <span class="font-mono text-gray-500">{{ source_experiment.id[:16] }}...</span>
                    <span class="text-gray-400">•</span>
                    Dataset: <span class="font-medium text-gray-900">{{ dataset.filename }}</span>
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
                                <label class="form-label">Question Field</label>
                                <input type="text" name="question_field" value="{{ cfg.data.question_field }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Answer Field</label>
                                <input type="text" name="answer_field" value="{{ cfg.data.answer_field }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Validation Split</label>
                                <input type="number" name="validation_split" value="{{ cfg.data.validation_split }}" step="0.05" min="0.05" max="0.5" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Random Seed</label>
                                <input type="number" name="seed" value="{{ cfg.data.seed }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Max Length</label>
                                <input type="number" name="max_length" value="{{ cfg.data.max_length }}" class="form-input">
                            </div>
                        </div>
                        <div class="form-group">
                            <label class="form-label">System Prompt</label>
                            <textarea name="system_prompt" rows="2" class="form-textarea">{{ cfg.data.system_prompt }}</textarea>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Chat Template <span class="text-gray-400 font-normal">(use {system_prompt}, {question}, {answer})</span></label>
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
                                <label class="form-label">Pretrained Model</label>
                                <input type="text" name="pretrained_model_name" value="{{ cfg.model.pretrained_model_name }}" class="form-input font-mono text-sm">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Pad Token Override</label>
                                <input type="text" name="pad_token_override" value="{{ cfg.model.pad_token_override or '' }}" class="form-input font-mono">
                            </div>
                            <div class="form-group flex items-center gap-3 pt-2">
                                <input type="checkbox" name="trust_remote_code" id="trust_remote_code" class="form-checkbox" {% if cfg.model.trust_remote_code %}checked{% endif %}>
                                <label for="trust_remote_code" class="text-sm text-gray-700">Trust Remote Code</label>
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
                        <div class="flex items-center gap-3 mb-4 pb-4 border-b border-gray-100">
                            <input type="checkbox" name="peft_enabled" id="peft_enabled" class="form-checkbox" {% if cfg.peft.enabled %}checked{% endif %}>
                            <label for="peft_enabled" class="text-sm font-medium text-gray-700">Enable LoRA Adapters</label>
                        </div>
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div class="form-group">
                                <label class="form-label">Rank (r)</label>
                                <input type="number" name="peft_r" value="{{ cfg.peft.r }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Alpha</label>
                                <input type="number" name="peft_lora_alpha" value="{{ cfg.peft.lora_alpha }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Dropout</label>
                                <input type="number" name="peft_lora_dropout" value="{{ cfg.peft.lora_dropout }}" step="0.01" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Bias</label>
                                <select name="peft_bias" class="form-select">
                                    <option value="none" {% if cfg.peft.bias == 'none' %}selected{% endif %}>none</option>
                                    <option value="lora_only" {% if cfg.peft.bias == 'lora_only' %}selected{% endif %}>lora_only</option>
                                    <option value="all" {% if cfg.peft.bias == 'all' %}selected{% endif %}>all</option>
                                </select>
                            </div>
                            <div class="form-group md:col-span-4">
                                <label class="form-label">Target Modules <span class="text-gray-400 font-normal">(comma-separated)</span></label>
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
                                <label class="form-label">Epochs</label>
                                <input type="number" name="num_train_epochs" value="{{ cfg.training.num_train_epochs }}" step="0.5" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Learning Rate</label>
                                <input type="text" name="learning_rate" value="{{ cfg.training.learning_rate }}" class="form-input font-mono">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Train Batch Size</label>
                                <input type="number" name="per_device_train_batch_size" value="{{ cfg.training.per_device_train_batch_size }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Eval Batch Size</label>
                                <input type="number" name="per_device_eval_batch_size" value="{{ cfg.training.per_device_eval_batch_size }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Weight Decay</label>
                                <input type="number" name="weight_decay" value="{{ cfg.training.weight_decay }}" step="0.01" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Warmup Ratio</label>
                                <input type="number" name="warmup_ratio" value="{{ cfg.training.warmup_ratio }}" step="0.01" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Gradient Accum Steps</label>
                                <input type="number" name="gradient_accumulation_steps" value="{{ cfg.training.gradient_accumulation_steps }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">LR Scheduler</label>
                                <select name="lr_scheduler_type" class="form-select">
                                    <option value="cosine" {% if cfg.training.lr_scheduler_type == 'cosine' %}selected{% endif %}>cosine</option>
                                    <option value="linear" {% if cfg.training.lr_scheduler_type == 'linear' %}selected{% endif %}>linear</option>
                                    <option value="constant" {% if cfg.training.lr_scheduler_type == 'constant' %}selected{% endif %}>constant</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label class="form-label">Logging Steps</label>
                                <input type="number" name="logging_steps" value="{{ cfg.training.logging_steps }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Eval Steps</label>
                                <input type="number" name="eval_steps" value="{{ cfg.training.eval_steps }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Save Steps</label>
                                <input type="number" name="save_steps" value="{{ cfg.training.save_steps }}" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Max Steps <span class="text-gray-400 font-normal">(-1 = off)</span></label>
                                <input type="number" name="max_steps" value="{{ cfg.training.max_steps }}" class="form-input">
                            </div>
                        </div>
                        <div class="flex flex-wrap gap-6 mt-4 pt-4 border-t border-gray-100">
                            <label class="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" name="gradient_checkpointing" class="form-checkbox" {% if cfg.training.gradient_checkpointing %}checked{% endif %}>
                                <span class="text-sm text-gray-700">Gradient Checkpointing</span>
                            </label>
                            <label class="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" name="fp16" class="form-checkbox" {% if cfg.training.fp16 %}checked{% endif %}>
                                <span class="text-sm text-gray-700">FP16</span>
                            </label>
                            <label class="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" name="bf16" class="form-checkbox" {% if cfg.training.bf16 %}checked{% endif %}>
                                <span class="text-sm text-gray-700">BF16</span>
                            </label>
                        </div>
                    </div>
                </div>
                
                <div class="flex justify-end gap-3">
                    <a href="/experiments/{{ source_experiment.id }}" class="px-4 py-2 text-gray-700 font-medium hover:bg-gray-100 rounded-lg transition-all">Cancel</a>
                    <button type="submit" class="btn-success px-8">Start Training</button>
                </div>
            </form>
        </div>
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
                <h1 class="text-2xl font-bold text-gray-900">Experiments</h1>
                <p class="text-gray-600">Track and manage your training runs</p>
            </div>
            <a href="/datasets" class="btn-primary">New Experiment</a>
        </div>
        
        <div class="card">
            <div class="overflow-x-auto">
                <table class="w-full">
                    <thead>
                        <tr class="bg-gray-50 border-b border-gray-200">
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">ID</th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Type</th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Dataset</th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Model</th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Status</th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Started</th>
                            <th class="px-6 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Actions</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        {% for exp in experiments %}
                        <tr class="hover:bg-gray-50 transition-colors">
                            <td class="px-6 py-4 font-mono text-sm text-gray-600">{{ exp.id[:8] }}</td>
                            <td class="px-6 py-4">
                                {% if exp.experiment_type == 'causal_lm' %}
                                <span class="badge badge-green">Causal</span>
                                {% else %}
                                <span class="badge badge-blue">MLM</span>
                                {% endif %}
                            </td>
                            <td class="px-6 py-4 text-sm text-gray-600">{{ exp.dataset_filename or 'N/A' }}</td>
                            <td class="px-6 py-4 text-sm text-gray-600 font-mono">{{ exp.config.model.pretrained_model_name | truncate(20) }}</td>
                            <td class="px-6 py-4">
                                {% if exp.status == 'completed' %}
                                <span class="badge badge-green">Completed</span>
                                {% elif exp.status == 'running' %}
                                <span class="badge badge-blue">Running</span>
                                {% elif exp.status == 'failed' %}
                                <span class="badge badge-red">Failed</span>
                                {% else %}
                                <span class="badge badge-gray">Pending</span>
                                {% endif %}
                            </td>
                            <td class="px-6 py-4 text-sm text-gray-500">{{ exp.started_at[:16] }}</td>
                            <td class="px-6 py-4 text-right">
                                <a href="/experiments/{{ exp.id }}" class="text-sm font-medium text-primary-600 hover:text-primary-800">View Details</a>
                            </td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="7" class="px-6 py-12 text-center text-gray-500">
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
        {% endblock %}""",
    )
)

EXPERIMENT_DETAIL_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Experiment Details - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="flex items-center justify-between mb-6">
            <div class="flex items-center gap-3">
                {% if experiment.experiment_type == 'causal_lm' %}
                <span class="badge badge-green">Causal LM</span>
                {% else %}
                <span class="badge badge-blue">Masked LM</span>
                {% endif %}
                <h1 class="text-2xl font-bold text-gray-900">Experiment Details</h1>
            </div>
            <div class="flex items-center gap-3">
                <a href="/experiments/{{ experiment.id }}/copy" class="btn-primary flex items-center gap-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                    Copy & Edit
                </a>
                <a href="/experiments" class="text-sm font-medium text-gray-600 hover:text-gray-900">&larr; Back to Experiments</a>
            </div>
        </div>
        
        <!-- Status Card -->
        <div class="card mb-6">
            <div class="card-body">
                <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
                    <div>
                        <p class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Experiment ID</p>
                        <p class="font-mono text-sm text-gray-900">{{ experiment.id[:16] }}...</p>
                    </div>
                    <div>
                        <p class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Status</p>
                        {% if experiment.status == 'completed' %}
                        <span class="badge badge-green">Completed</span>
                        {% elif experiment.status == 'running' %}
                        <span class="badge badge-blue">Running</span>
                        {% elif experiment.status == 'failed' %}
                        <span class="badge badge-red">Failed</span>
                        {% else %}
                        <span class="badge badge-gray">Pending</span>
                        {% endif %}
                    </div>
                    <div>
                        <p class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Dataset</p>
                        <p class="text-sm text-gray-900">{{ experiment.dataset_filename or 'N/A' }}</p>
                    </div>
                    <div>
                        <p class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Model</p>
                        <p class="font-mono text-sm text-gray-900">{{ experiment.config.model.pretrained_model_name | truncate(25) }}</p>
                    </div>
                    <div>
                        <p class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Started</p>
                        <p class="text-sm text-gray-900">{{ experiment.started_at[:19] }}</p>
                    </div>
                    <div>
                        <p class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Completed</p>
                        <p class="text-sm text-gray-900">{{ experiment.completed_at[:19] if experiment.completed_at else 'In progress...' }}</p>
                    </div>
                    {% if experiment.output_dir %}
                    <div class="col-span-2">
                        <p class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Output Directory</p>
                        <p class="font-mono text-sm text-gray-900">{{ experiment.output_dir }}</p>
                    </div>
                    {% endif %}
                </div>
                {% if experiment.error %}
                <div class="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                    <p class="text-sm font-medium text-red-800">Error</p>
                    <p class="text-sm text-red-700 mt-1">{{ experiment.error }}</p>
                </div>
                {% endif %}
                
            </div>
        </div>
        
        {% if experiment.status == 'running' or experiment.status == 'pending' %}
        <!-- Sticky Progress Bar -->
        <div class="sticky top-16 z-40 -mx-4 px-4 py-3 bg-white/95 backdrop-blur-sm border-b border-gray-200 shadow-sm">
            <div class="flex items-center gap-4">
                <div class="flex-1">
                    <div class="flex items-center justify-between mb-1">
                        <p class="text-xs font-medium text-gray-500 uppercase tracking-wide">Training Progress</p>
                        <div class="flex items-center gap-4 text-xs text-gray-500">
                            <span id="progress-step">Step: --</span>
                            <span id="progress-epoch">Epoch: -- / {{ experiment.config.training.num_train_epochs }}</span>
                        </div>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                        <div id="progress-bar" class="progress-bar-animated h-2.5 rounded-full transition-all duration-500 ease-out" style="width: 0%"></div>
                    </div>
                </div>
                <p id="progress-text" class="text-lg font-semibold text-blue-600 min-w-[4rem] text-right">0%</p>
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
                <h2 class="font-semibold text-gray-800">Training Metrics</h2>
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
                <h2 class="font-semibold text-gray-800">Configuration</h2>
            </div>
            <div class="card-body space-y-6">
                <!-- Data Config -->
                <div>
                    <h3 class="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3 flex items-center gap-2">
                        <svg class="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"></path></svg>
                        Data
                    </h3>
                    <div class="bg-gray-50 rounded-lg p-4">
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                            {% for key, value in experiment.config.data.items() %}
                            <div>
                                <span class="text-gray-500">{{ key }}:</span>
                                <span class="text-gray-900 ml-1 font-medium">{{ value if value is not none else 'N/A' }}</span>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
                
                <!-- Model Config -->
                <div>
                    <h3 class="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3 flex items-center gap-2">
                        <svg class="w-4 h-4 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                        Model
                    </h3>
                    <div class="bg-gray-50 rounded-lg p-4">
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                            {% for key, value in experiment.config.model.items() %}
                            <div>
                                <span class="text-gray-500">{{ key }}:</span>
                                <span class="text-gray-900 ml-1 font-medium">{{ value if value is not none else 'N/A' }}</span>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
                
                <!-- Training Config -->
                <div>
                    <h3 class="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3 flex items-center gap-2">
                        <svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                        Training
                    </h3>
                    <div class="bg-gray-50 rounded-lg p-4">
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                            {% for key, value in experiment.config.training.items() %}
                            <div>
                                <span class="text-gray-500">{{ key }}:</span>
                                <span class="text-gray-900 ml-1 font-medium">{{ value if value is not none else 'N/A' }}</span>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
                
                <!-- PEFT Config -->
                {% if experiment.config.peft %}
                <div>
                    <h3 class="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3 flex items-center gap-2">
                        <svg class="w-4 h-4 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"></path></svg>
                        PEFT / LoRA
                    </h3>
                    <div class="bg-gray-50 rounded-lg p-4">
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                            {% for key, value in experiment.config.peft.items() %}
                            <div>
                                <span class="text-gray-500">{{ key }}:</span>
                                <span class="text-gray-900 ml-1 font-medium">{{ value if value is not none else 'N/A' }}</span>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
                {% endif %}
            </div>
        </div>
        
        <!-- Training Logs -->
        <div class="card mt-6">
            <div class="card-header flex items-center justify-between">
                <h2 class="font-semibold text-gray-800 flex items-center gap-2">
                    <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                    Training Logs
                    {% if experiment.status == 'running' or experiment.status == 'pending' %}
                    <span id="logs-status" class="ml-2 text-xs font-medium text-blue-600">(live)</span>
                    {% endif %}
                </h2>
                <span id="logs-count" class="text-sm text-gray-500">{{ logs|length }} entries</span>
            </div>
            <div class="card-body">
                <div class="overflow-x-auto">
                    <table class="w-full text-sm">
                        <thead>
                            <tr class="bg-gray-50 border-b border-gray-200">
                                <th class="px-4 py-2 text-left text-xs font-semibold text-gray-600 uppercase">Step</th>
                                <th class="px-4 py-2 text-left text-xs font-semibold text-gray-600 uppercase">Epoch</th>
                                <th class="px-4 py-2 text-left text-xs font-semibold text-gray-600 uppercase">Loss</th>
                                <th class="px-4 py-2 text-left text-xs font-semibold text-gray-600 uppercase">Eval Loss</th>
                                <th class="px-4 py-2 text-left text-xs font-semibold text-gray-600 uppercase">Learning Rate</th>
                                <th class="px-4 py-2 text-left text-xs font-semibold text-gray-600 uppercase">Grad Norm</th>
                            </tr>
                        </thead>
                        <tbody id="logs-table-body" class="divide-y divide-gray-100">
                            {% for entry in logs %}
                            <tr class="hover:bg-gray-50">
                                <td class="px-4 py-2 font-mono text-gray-900">{{ entry.step if entry.step is defined else '-' }}</td>
                                <td class="px-4 py-2 text-gray-700">{{ "%.2f"|format(entry.epoch) if entry.epoch is defined else '-' }}</td>
                                <td class="px-4 py-2 text-gray-700">{{ "%.4f"|format(entry.loss) if entry.loss is defined else '-' }}</td>
                                <td class="px-4 py-2 text-gray-700">{{ "%.4f"|format(entry.eval_loss) if entry.eval_loss is defined else '-' }}</td>
                                <td class="px-4 py-2 font-mono text-gray-600 text-xs">{{ "%.2e"|format(entry.learning_rate) if entry.learning_rate is defined else '-' }}</td>
                                <td class="px-4 py-2 text-gray-700">{{ "%.2f"|format(entry.grad_norm) if entry.grad_norm is defined else '-' }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% if not logs %}
                <p id="no-logs-msg" class="text-center text-gray-500 py-4">No logs available yet</p>
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
                            <tr class="hover:bg-gray-50">
                                <td class="px-4 py-2 font-mono text-gray-900">${entry.step !== undefined ? entry.step : '-'}</td>
                                <td class="px-4 py-2 text-gray-700">${formatNumber(entry.epoch, 2)}</td>
                                <td class="px-4 py-2 text-gray-700">${formatNumber(entry.loss, 4)}</td>
                                <td class="px-4 py-2 text-gray-700">${formatNumber(entry.eval_loss, 4)}</td>
                                <td class="px-4 py-2 font-mono text-gray-600 text-xs">${formatScientific(entry.learning_rate)}</td>
                                <td class="px-4 py-2 text-gray-700">${formatNumber(entry.grad_norm, 2)}</td>
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
        {% endblock %}""",
    )
)


BENCHMARKS_TEMPLATE = (
    BASE_TEMPLATE.replace("{% block title %}AIP-C01 Prep{% endblock %}", "{% block title %}Benchmarks - AIP-C01 Prep{% endblock %}")
    .replace(
        "{% block content %}{% endblock %}",
        """{% block content %}
        <div class="mb-6">
            <h1 class="text-2xl font-bold text-gray-900">Benchmarks</h1>
            <p class="text-gray-600">Create question/answer pairs to evaluate experiments with BLEU scores</p>
        </div>
        
        <div class="card mb-6">
            <div class="card-header">
                <h2 class="font-semibold text-gray-800">Create New Benchmark</h2>
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
                        <tr class="bg-gray-50 border-b border-gray-200">
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Name</th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Question</th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Gold Answer</th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Created</th>
                            <th class="px-6 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Actions</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        {% for benchmark in benchmarks %}
                        <tr class="hover:bg-gray-50 transition-colors">
                            <td class="px-6 py-4 font-medium text-gray-900">{{ benchmark.name }}</td>
                            <td class="px-6 py-4 text-sm text-gray-600">{{ benchmark.question | truncate(50) }}</td>
                            <td class="px-6 py-4 text-sm text-gray-600">{{ benchmark.gold_answer | truncate(50) }}</td>
                            <td class="px-6 py-4 text-sm text-gray-500">{{ benchmark.created_at[:10] }}</td>
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
                            <td colspan="5" class="px-6 py-12 text-center text-gray-500">
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
                    <h1 class="text-2xl font-bold text-gray-900">Run Evaluation</h1>
                </div>
            </div>
            
            <div class="section-card mb-6">
                <div class="section-header">
                    <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    <h2 class="section-title">Benchmark Details</h2>
                </div>
                <div class="section-body space-y-3">
                    <div>
                        <p class="text-xs font-medium text-gray-500 uppercase mb-1">Question</p>
                        <p class="text-sm text-gray-900 bg-gray-50 p-3 rounded-lg">{{ benchmark.question }}</p>
                    </div>
                    <div>
                        <p class="text-xs font-medium text-emerald-600 uppercase mb-1">Gold Answer</p>
                        <p class="text-sm text-gray-900 bg-emerald-50 p-3 rounded-lg border border-emerald-200">{{ benchmark.gold_answer }}</p>
                    </div>
                </div>
            </div>
            
            <form action="/benchmarks/{{ benchmark.id }}/evaluate" method="post" class="space-y-6">
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
                            <p class="text-xs text-gray-500 mt-1">Only completed experiments with trained models are shown</p>
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
                                <label class="form-label">Max New Tokens</label>
                                <input type="number" name="max_new_tokens" value="128" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Temperature</label>
                                <input type="number" name="temperature" value="0.7" step="0.1" class="form-input">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Top-P</label>
                                <input type="number" name="top_p" value="0.9" step="0.05" class="form-input">
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="flex justify-end gap-3">
                    <a href="/benchmarks" class="px-4 py-2 text-gray-700 font-medium hover:bg-gray-100 rounded-lg transition-all">Cancel</a>
                    <button type="submit" class="btn-primary px-8">Start Evaluation</button>
                </div>
            </form>
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
                <h1 class="text-2xl font-bold text-gray-900">Evaluation Results</h1>
                <p class="text-gray-600">Benchmark: <span class="font-medium">{{ benchmark.name }}</span></p>
            </div>
            <a href="/benchmarks" class="text-sm font-medium text-gray-600 hover:text-gray-900">&larr; Back to Benchmarks</a>
        </div>
        
        <div class="section-card mb-6">
            <div class="section-header">
                <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                <h2 class="section-title">Benchmark Details</h2>
            </div>
            <div class="section-body space-y-3">
                <div>
                    <p class="text-xs font-medium text-gray-500 uppercase mb-1">Question</p>
                    <p class="text-sm text-gray-900 bg-gray-50 p-3 rounded-lg">{{ benchmark.question }}</p>
                </div>
                <div>
                    <p class="text-xs font-medium text-emerald-600 uppercase mb-1">Gold Answer</p>
                    <p class="text-sm text-gray-900 bg-emerald-50 p-3 rounded-lg border border-emerald-200">{{ benchmark.gold_answer }}</p>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <h2 class="font-semibold text-gray-800">Evaluation Runs</h2>
            </div>
            <div class="divide-y divide-gray-100">
                {% for eval in evaluations %}
                <div class="p-6">
                    <div class="flex items-center justify-between mb-4">
                        <div class="flex items-center gap-3">
                            <span class="font-mono text-sm text-gray-500">{{ eval.id[:8] }}</span>
                            {% if eval.status == 'completed' %}
                            <span class="badge badge-green">Completed</span>
                            {% elif eval.status == 'running' %}
                            <span class="badge badge-blue">Running</span>
                            {% elif eval.status == 'failed' %}
                            <span class="badge badge-red">Failed</span>
                            {% else %}
                            <span class="badge badge-gray">Pending</span>
                            {% endif %}
                        </div>
                        <div class="text-right">
                            {% if eval.status == 'completed' %}
                            <p class="text-3xl font-bold {% if eval.bleu_score > 50 %}text-emerald-600{% elif eval.bleu_score > 20 %}text-amber-600{% else %}text-red-600{% endif %}">{{ "%.2f"|format(eval.bleu_score) }}</p>
                            <p class="text-xs text-gray-500 uppercase">BLEU Score</p>
                            {% endif %}
                        </div>
                    </div>
                    <div class="text-sm text-gray-500 mb-3">
                        Experiment: <span class="font-mono">{{ eval.experiment_id[:8] }}</span> • {{ eval.started_at[:16] }}
                    </div>
                    {% if eval.status == 'completed' %}
                    <div>
                        <p class="text-xs font-medium text-blue-600 uppercase mb-1">Model Answer</p>
                        <p class="text-sm text-gray-900 bg-blue-50 p-3 rounded-lg border border-blue-200">{{ eval.model_answer }}</p>
                    </div>
                    {% endif %}
                    {% if eval.error %}
                    <div class="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                        <p class="text-sm text-red-700">{{ eval.error }}</p>
                    </div>
                    {% endif %}
                </div>
                {% else %}
                <div class="px-6 py-12 text-center text-gray-500">
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
                <h1 class="text-2xl font-bold text-gray-900">Evaluation Details</h1>
            </div>
            <a href="/benchmarks" class="text-sm font-medium text-gray-600 hover:text-gray-900">&larr; Back to Benchmarks</a>
        </div>
        
        <!-- Summary Card -->
        <div class="card mb-6">
            <div class="card-body">
                <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
                    <div>
                        <p class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Status</p>
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
                        <p class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Experiment</p>
                        <a href="/experiments/{{ evaluation.experiment_id }}" class="font-mono text-sm text-primary-600 hover:text-primary-800 hover:underline">{{ evaluation.experiment_id[:8] }}...</a>
                    </div>
                    <div>
                        <p class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Started</p>
                        <p class="text-sm text-gray-900">{{ evaluation.started_at[:19] }}</p>
                    </div>
                    <div>
                        <p class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Completed</p>
                        <p class="text-sm text-gray-900">{{ evaluation.completed_at[:19] if evaluation.completed_at else 'In progress...' }}</p>
                    </div>
                </div>
                {% if evaluation.error %}
                <div class="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                    <p class="text-sm font-medium text-red-800">Error</p>
                    <p class="text-sm text-red-700 mt-1">{{ evaluation.error }}</p>
                </div>
                {% endif %}
            </div>
        </div>
        
        <!-- BLEU Score -->
        {% if evaluation.status == 'completed' %}
        <div class="metric-card mb-6 text-center py-8">
            <p class="metric-label mb-2">BLEU Score</p>
            <p class="text-5xl font-bold {% if evaluation.bleu_score > 50 %}text-emerald-600{% elif evaluation.bleu_score > 20 %}text-amber-600{% else %}text-red-600{% endif %}">{{ "%.2f"|format(evaluation.bleu_score) }}</p>
        </div>
        {% endif %}
        
        <!-- Q&A Comparison -->
        <div class="card">
            <div class="card-header">
                <h2 class="font-semibold text-gray-800">Question & Answer Comparison</h2>
            </div>
            <div class="card-body space-y-4">
                <div>
                    <p class="text-xs font-medium text-gray-500 uppercase mb-1">Question</p>
                    <p class="text-sm text-gray-900 bg-gray-50 p-3 rounded-lg">{{ evaluation.question }}</p>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <p class="text-xs font-medium text-emerald-600 uppercase mb-1">Gold Answer</p>
                        <p class="text-sm text-gray-900 bg-emerald-50 p-3 rounded-lg border border-emerald-200 min-h-24">{{ evaluation.gold_answer }}</p>
                    </div>
                    <div>
                        <p class="text-xs font-medium text-blue-600 uppercase mb-1">Model Answer</p>
                        <p class="text-sm text-gray-900 bg-blue-50 p-3 rounded-lg border border-blue-200 min-h-24">{{ evaluation.model_answer or 'Pending...' }}</p>
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
            <h1 class="text-2xl font-bold text-gray-900">Model Benchmark Comparisons</h1>
            <p class="text-gray-600">Compare BLEU scores and settings across all evaluated models</p>
        </div>
        
        {% if evaluations %}
        <div class="card mb-6">
            <div class="card-header flex items-center justify-between">
                <h2 class="font-semibold text-gray-800">BLEU Score Leaderboard</h2>
                <span class="text-sm text-gray-500">{{ evaluations | length }} evaluation(s)</span>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full">
                    <thead>
                        <tr class="bg-gray-50 border-b border-gray-200">
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Rank</th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">BLEU</th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Benchmark</th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Model</th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Dataset</th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">LR</th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Epochs</th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Batch</th>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">LoRA</th>
                            <th class="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Actions</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        {% for eval in evaluations %}
                        <tr class="hover:bg-gray-50 transition-colors">
                            <td class="px-4 py-4">
                                {% if loop.index == 1 %}
                                <span class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-yellow-100 text-yellow-700 font-bold">1</span>
                                {% elif loop.index == 2 %}
                                <span class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-gray-200 text-gray-700 font-bold">2</span>
                                {% elif loop.index == 3 %}
                                <span class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-amber-100 text-amber-700 font-bold">3</span>
                                {% else %}
                                <span class="text-gray-500 font-medium pl-2">{{ loop.index }}</span>
                                {% endif %}
                            </td>
                            <td class="px-4 py-4">
                                <span class="text-xl font-bold {% if eval.bleu_score > 50 %}text-emerald-600{% elif eval.bleu_score > 20 %}text-amber-600{% else %}text-red-600{% endif %}">{{ "%.2f"|format(eval.bleu_score) }}</span>
                            </td>
                            <td class="px-4 py-4">
                                <span class="font-medium text-gray-900">{{ eval.benchmark_name }}</span>
                            </td>
                            <td class="px-4 py-4">
                                <span class="text-sm font-mono text-gray-700">{{ eval.model_name | truncate(30) }}</span>
                            </td>
                            <td class="px-4 py-4">
                                <span class="text-sm text-gray-600">{{ eval.dataset_filename | truncate(20) }}</span>
                            </td>
                            <td class="px-4 py-4">
                                <span class="text-sm font-mono text-gray-600">{{ "%.0e"|format(eval.learning_rate) }}</span>
                            </td>
                            <td class="px-4 py-4">
                                <span class="text-sm text-gray-600">{{ eval.num_epochs }}</span>
                            </td>
                            <td class="px-4 py-4">
                                <span class="text-sm text-gray-600">{{ eval.batch_size }}</span>
                            </td>
                            <td class="px-4 py-4">
                                {% if eval.lora_r %}
                                <span class="badge badge-blue">r={{ eval.lora_r }} α={{ eval.lora_alpha }}</span>
                                {% else %}
                                <span class="text-sm text-gray-400">—</span>
                                {% endif %}
                            </td>
                            <td class="px-4 py-4 text-right">
                                <a href="/experiments/{{ eval.experiment_id }}" class="text-sm font-medium text-gray-600 hover:text-gray-800 mr-3">Experiment</a>
                                <a href="/evaluations/{{ eval.eval_id }}" class="text-sm font-medium text-primary-600 hover:text-primary-800">Details</a>
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
                <p class="metric-label mb-2">Best BLEU Score</p>
                <p class="metric-value">{{ "%.2f"|format(evaluations[0].bleu_score) if evaluations else "—" }}</p>
                <p class="text-xs text-gray-500 mt-1">{{ evaluations[0].model_name | truncate(25) if evaluations else "" }}</p>
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
        {% else %}
        <div class="card">
            <div class="px-6 py-12 text-center text-gray-500">
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


@app.route("/")
def index():
    return render_template_string(HOME_TEMPLATE)


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


@app.route("/configs/<config_name>")
def config_detail(config_name: str):
    import yaml
    resp = requests.get(f"{API_BASE_URL}/configs/{config_name}", timeout=10)
    if resp.status_code != 200:
        return redirect(url_for("configs_page"))
    config_data = resp.json()
    config_data.pop("_experiment_type", None)
    config_yaml = yaml.dump(config_data, default_flow_style=False)
    return render_template_string(CONFIG_DETAIL_TEMPLATE, config_name=config_name, config_yaml=config_yaml)


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
    text_fields = [f.strip() for f in form.pop("text_fields", "").split(",") if f.strip()]
    
    payload = {
        "dataset_id": form.get("dataset_id"),
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
            },
        },
    }
    requests.post(f"{API_BASE_URL}/experiments/masked-lm", json=payload, timeout=10)
    return redirect(url_for("experiments_page"))


@app.route("/experiments/causal-lm", methods=["POST"])
def start_causal_lm():
    form = request.form.to_dict()
    target_modules = [m.strip() for m in form.get("peft_target_modules", "").split(",") if m.strip()]
    
    payload = {
        "dataset_id": form.get("dataset_id"),
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
            },
        },
    }
    requests.post(f"{API_BASE_URL}/experiments/causal-lm", json=payload, timeout=10)
    return redirect(url_for("experiments_page"))


@app.route("/experiments")
def experiments_page():
    resp = requests.get(f"{API_BASE_URL}/experiments", timeout=10)
    data = resp.json()
    return render_template_string(EXPERIMENTS_TEMPLATE, experiments=data.get("experiments", []))


@app.route("/experiments/<experiment_id>")
def experiment_detail(experiment_id: str):
    resp = requests.get(f"{API_BASE_URL}/experiments/{experiment_id}", timeout=10)
    if resp.status_code != 200:
        return redirect(url_for("experiments_page"))
    logs_resp = requests.get(f"{API_BASE_URL}/experiments/{experiment_id}/logs", timeout=10)
    logs = logs_resp.json().get("logs", []) if logs_resp.status_code == 200 else []
    return render_template_string(EXPERIMENT_DETAIL_TEMPLATE, experiment=resp.json(), logs=logs)


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
    requests.post(f"{API_BASE_URL}/benchmarks/{benchmark_id}/evaluate", json=payload, timeout=10)
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

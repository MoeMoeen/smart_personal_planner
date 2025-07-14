// Smart Personal Planner Frontend JavaScript

const API_BASE_URL = 'http://localhost:8000';

// DOM elements
const goalForm = document.getElementById('goalForm');
const goalTypeSelect = document.getElementById('goalType');
const habitFields = document.getElementById('habitFields');
const endDateGroup = document.getElementById('endDateGroup');
const generatePlanBtn = document.getElementById('generatePlan');
const aiGoalDescription = document.getElementById('aiGoalDescription');
const aiPlanResult = document.getElementById('aiPlanResult');
const planOutput = document.getElementById('planOutput');
const goalsList = document.getElementById('goalsList');

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    loadGoals();
});

function setupEventListeners() {
    // Goal type change handler
    goalTypeSelect.addEventListener('change', function() {
        const goalType = this.value;
        const endDateInput = document.getElementById('endDate');
        
        if (goalType === 'habit') {
            habitFields.style.display = 'block';
            endDateInput.required = false;
            endDateGroup.querySelector('label').textContent = 'End Date (optional):';
        } else if (goalType === 'project') {
            habitFields.style.display = 'none';
            endDateInput.required = true;
            endDateGroup.querySelector('label').textContent = 'End Date:';
        } else {
            habitFields.style.display = 'none';
            endDateInput.required = false;
        }
    });

    // Goal form submission
    goalForm.addEventListener('submit', handleGoalSubmission);

    // AI plan generation
    generatePlanBtn.addEventListener('click', handleAIPlanGeneration);
}

async function handleGoalSubmission(event) {
    event.preventDefault();
    
    const formData = new FormData(goalForm);
    const goalType = formData.get('goalType');
    
    try {
        const goalData = {
            title: formData.get('title'),
            description: formData.get('description') || null,
            start_date: formData.get('startDate'),
            goal_type: goalType
        };

        if (goalType === 'project') {
            goalData.end_date = formData.get('endDate');
            const response = await fetch(`${API_BASE_URL}/goals/project/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(goalData)
            });
        } else if (goalType === 'habit') {
            goalData.end_date = formData.get('endDate') || null;
            goalData.recurrence_cycle = formData.get('recurrenceCycle');
            goalData.goal_frequency_per_cycle = parseInt(formData.get('frequencyPerCycle'));
            goalData.default_estimated_time_per_cycle = parseInt(formData.get('estimatedTime')) || 1;
            
            const response = await fetch(`${API_BASE_URL}/goals/habit/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(goalData)
            });
        }

        if (response.ok) {
            const result = await response.json();
            showNotification('Goal created successfully!', 'success');
            goalForm.reset();
            goalTypeSelect.dispatchEvent(new Event('change')); // Reset form display
            loadGoals();
        } else {
            const error = await response.json();
            showNotification(`Error: ${error.detail}`, 'error');
        }
    } catch (error) {
        showNotification(`Error: ${error.message}`, 'error');
    }
}

async function handleAIPlanGeneration() {
    const description = aiGoalDescription.value.trim();
    
    if (!description) {
        showNotification('Please enter a goal description', 'error');
        return;
    }

    generatePlanBtn.disabled = true;
    generatePlanBtn.textContent = 'Generating...';

    try {
        const response = await fetch(`${API_BASE_URL}/planning/ai-generate-plan`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ goal_description: description })
        });

        if (response.ok) {
            const result = await response.json();
            planOutput.textContent = JSON.stringify(result.plan, null, 2);
            aiPlanResult.style.display = 'block';
            showNotification('AI plan generated successfully!', 'success');
        } else {
            const error = await response.json();
            showNotification(`Error: ${error.detail}`, 'error');
        }
    } catch (error) {
        showNotification(`Error: ${error.message}`, 'error');
    } finally {
        generatePlanBtn.disabled = false;
        generatePlanBtn.textContent = 'Generate AI Plan';
    }
}

async function loadGoals() {
    try {
        const response = await fetch(`${API_BASE_URL}/goals/`);
        
        if (response.ok) {
            const goals = await response.json();
            displayGoals(goals);
        } else {
            console.error('Failed to load goals');
        }
    } catch (error) {
        console.error('Error loading goals:', error);
    }
}

function displayGoals(goals) {
    if (goals.length === 0) {
        goalsList.innerHTML = '<p>No goals created yet. Create your first goal above!</p>';
        return;
    }

    const goalsHTML = goals.map(goal => `
        <div class="goal-card">
            <h3>${goal.title}</h3>
            <p><strong>Type:</strong> ${goal.goal_type}</p>
            <p><strong>Progress:</strong> ${goal.progress}%</p>
            <p><strong>Start Date:</strong> ${goal.start_date}</p>
            ${goal.end_date ? `<p><strong>End Date:</strong> ${goal.end_date}</p>` : ''}
            ${goal.description ? `<p><strong>Description:</strong> ${goal.description}</p>` : ''}
            <div class="goal-actions">
                <button onclick="deleteGoal(${goal.id})" class="delete-btn">Delete</button>
            </div>
        </div>
    `).join('');

    goalsList.innerHTML = goalsHTML;
}

async function deleteGoal(goalId) {
    if (!confirm('Are you sure you want to delete this goal?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/goals/${goalId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showNotification('Goal deleted successfully!', 'success');
            loadGoals();
        } else {
            const error = await response.json();
            showNotification(`Error: ${error.detail}`, 'error');
        }
    } catch (error) {
        showNotification(`Error: ${error.message}`, 'error');
    }
}

function showNotification(message, type) {
    // Create a simple notification system
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.remove();
    }, 3000);
}
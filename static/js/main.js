document.addEventListener('DOMContentLoaded', function() {
    // Time slot selection
    document.querySelectorAll('.time-slot').forEach(slot => {
        slot.addEventListener('click', function() {
            document.querySelectorAll('.time-slot').forEach(s => s.classList.remove('selected'));
            this.classList.add('selected');
            document.getElementById('time').value = this.dataset.time;
        });
    });
    
    // Date selection for booking
    const dateInput = document.getElementById('date');
    if (dateInput) {
        dateInput.addEventListener('change', function() {
            const doctorId = this.dataset.doctor;
            const date = this.value;
            
            if (doctorId && date) {
                fetch(`/api/doctor/${doctorId}/slots?date=${date}`)
                    .then(response => response.json())
                    .then(data => {
                        const slotsContainer = document.getElementById('time-slots');
                        slotsContainer.innerHTML = '';
                        
                        if (data.slots && data.slots.length > 0) {
                            data.slots.forEach(slot => {
                                const slotElement = document.createElement('span');
                                slotElement.className = 'time-slot';
                                slotElement.dataset.time = slot;
                                slotElement.textContent = slot;
                                slotsContainer.appendChild(slotElement);
                            });
                        } else {
                            slotsContainer.innerHTML = '<p>No available slots for this date</p>';
                        }
                    });
            }
        });
    }
    
    // Add availability time slot
    const addSlotBtn = document.getElementById('add-slot');
    if (addSlotBtn) {
        addSlotBtn.addEventListener('click', function() {
            const container = document.getElementById('availability-slots');
            const newSlot = document.createElement('div');
            newSlot.className = 'availability-day mb-3 p-3 bg-light rounded';
            newSlot.innerHTML = `
                <div class="row">
                    <div class="col-md-3">
                        <select name="day" class="form-select">
                            <option value="0">Monday</option>
                            <option value="1">Tuesday</option>
                            <option value="2">Wednesday</option>
                            <option value="3">Thursday</option>
                            <option value="4">Friday</option>
                            <option value="5">Saturday</option>
                            <option value="6">Sunday</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <input type="time" name="start_time" class="form-control">
                    </div>
                    <div class="col-md-3">
                        <input type="time" name="end_time" class="form-control">
                    </div>
                    <div class="col-md-3">
                        <button type="button" class="btn btn-danger remove-slot">Remove</button>
                    </div>
                </div>
            `;
            container.appendChild(newSlot);
            
            // Add event listener to remove button
            newSlot.querySelector('.remove-slot').addEventListener('click', function() {
                container.removeChild(newSlot);
            });
        });
    }
    
    // Remove availability time slot
    document.querySelectorAll('.remove-slot').forEach(btn => {
        btn.addEventListener('click', function() {
            this.closest('.availability-day').remove();
        });
    });
});
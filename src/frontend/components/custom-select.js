/* src/frontend/ui/custom-select.js */
/* V2.0 - Dropdown intelligent qui s'ouvre vers le haut */
export class CustomSelect {
    constructor(originalSelect) {
        this.originalSelect = originalSelect;
        this.wrapper = this.originalSelect.closest('.custom-select-wrapper');
        this.customSelect = document.createElement("div");
        this.customSelect.classList.add("custom-select");

        this.originalSelect.style.display = "none";
        this.wrapper.appendChild(this.customSelect);

        this.render();
        
        this.trigger = this.customSelect.querySelector(".custom-select__trigger");
        this.options = this.customSelect.querySelector(".custom-select__options");
        
        this.addEventListeners();
    }

    render() {
        const selectedOption = this.originalSelect.options[this.originalSelect.selectedIndex];
        const selectedHTML = selectedOption ? selectedOption.innerHTML : '<span>&nbsp;</span>';

        this.customSelect.innerHTML = `
            <div class="custom-select__trigger">
                <span>${selectedHTML}</span>
                <div class="custom-select__arrow"></div>
            </div>
            <div class="custom-select__options">
                ${[...this.originalSelect.options].map(option => `
                    <div class="custom-select__option ${option.selected ? 'is-selected' : ''}" data-value="${option.value}">
                        ${option.innerHTML}
                    </div>
                `).join("")}
            </div>
        `;
    }

    addEventListeners() {
        this.trigger.addEventListener("click", () => this.toggleOpen());

        document.addEventListener("click", (e) => {
            if (!this.wrapper.contains(e.target)) {
                this.close();
            }
        });
        
        this.customSelect.querySelectorAll(".custom-select__option").forEach(optionEl => {
            optionEl.addEventListener("click", (e) => {
                e.stopPropagation(); // Évite que le clic se propage et ferme le menu immédiatement
                this.selectOption(optionEl);
            });
        });
    }

    toggleOpen() {
        // AJOUT : La logique d'ouverture intelligente
        this.handlePositioning();
        this.wrapper.classList.toggle("is-open");
    }

    close() {
        if (this.wrapper.classList.contains('is-open')) {
            this.wrapper.classList.remove("is-open");
            // On nettoie la classe de positionnement à la fermeture
            this.wrapper.classList.remove("is-opening-up");
        }
    }
    
    selectOption(optionEl) {
        const value = optionEl.dataset.value;
        this.originalSelect.value = value;
        
        this.trigger.querySelector("span").innerHTML = optionEl.innerHTML;
        
        this.customSelect.querySelector('.is-selected')?.classList.remove('is-selected');
        optionEl.classList.add('is-selected');
        
        this.close();
        this.originalSelect.dispatchEvent(new Event('change'));
    }

    // AJOUT : Nouvelle méthode pour gérer la position
    handlePositioning() {
        const triggerRect = this.trigger.getBoundingClientRect();
        const optionsHeight = this.options.offsetHeight; // Hauteur réelle des options
        const spaceBelow = window.innerHeight - triggerRect.bottom;

        // On prend une marge de sécurité (20px)
        if (spaceBelow < optionsHeight + 20) {
            this.wrapper.classList.add("is-opening-up");
        } else {
            this.wrapper.classList.remove("is-opening-up");
        }
    }
}
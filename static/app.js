// AquaRAG Application Scripts

document.addEventListener("DOMContentLoaded", () => {
    // State management
    const state = {
        activeTab: "chat-tab",
        stats: null,
        examSets: [],
        chatHistory: [],
        currentCitations: [],
        activeQuestionId: null,
    };

    // DOM Elements
    const navButtons = document.querySelectorAll(".nav-btn");
    const tabContents = document.querySelectorAll(".tab-content");
    const currentTabTitle = document.getElementById("current-tab-title");
    const currentTabDesc = document.getElementById("current-tab-desc");

    // Chat DOM
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatHistoryDiv = document.getElementById("chat-history");
    const sendBtn = document.getElementById("send-btn");
    const citationsPanel = document.getElementById("citations-panel");
    const citationsList = document.getElementById("citations-list");
    const closeCitationsBtn = document.getElementById("close-citations-btn");
    const suggestButtons = document.querySelectorAll(".suggest-btn");

    // Search DOM
    const searchQueryInput = document.getElementById("search-query");
    const searchSubmitBtn = document.getElementById("search-submit");
    const searchTopKRange = document.getElementById("search-top-k");
    const topKValSpan = document.getElementById("top-k-val");
    const searchResultsStats = document.getElementById("search-results-stats");
    const resultsCountSpan = document.getElementById("results-count");
    const searchResultsList = document.getElementById("search-results-list");

    // Explorer DOM
    const treeContainer = document.getElementById("tree-container");
    const explorerFilter = document.getElementById("explorer-filter");
    const contentPlaceholder = document.getElementById("content-placeholder");
    const questionDetailArticle = document.getElementById("question-detail");
    const detailExamSet = document.getElementById("detail-exam-set");
    const detailQTitle = document.getElementById("detail-q-title");
    const detailQNum = document.getElementById("detail-q-num");
    const detailContent = document.getElementById("detail-content");

    // Stats DOM
    const statExamSets = document.getElementById("stat-exam-sets");
    const statQuestions = document.getElementById("stat-questions");
    const statDbSize = document.getElementById("stat-db-size");

    // Modal DOM
    const citationModal = document.getElementById("citation-modal");
    const modalExamSet = document.getElementById("modal-exam-set");
    const modalTitle = document.getElementById("modal-title");
    const modalContent = document.getElementById("modal-content");
    const modalCloseBtn = document.getElementById("modal-close-btn");

    // Settings DOM
    const settingsModal = document.getElementById("settings-modal");
    const settingsToggleBtn = document.getElementById("settings-toggle-btn");
    const settingsCloseBtn = document.getElementById("settings-close-btn");
    const settingsSaveBtn = document.getElementById("settings-save-btn");
    const settingsClearBtn = document.getElementById("settings-clear-btn");
    const userGeminiKeyInput = document.getElementById("user-gemini-key");
    const toggleKeyVisibilityBtn = document.getElementById("toggle-key-visibility");

    // TAB TITLES AND DESCRIPTIONS
    const tabInfo = {
        "chat-tab": {
            title: "RAG 智能對話",
            desc: "基於 082 年至 114 年國家考試「魚類生理學」歷屆 300 題專家解答進行檢索生成"
        },
        "search-tab": {
            title: "歷屆試題語意搜尋",
            desc: "利用 nomic-embed-text 語意向量進行考題與解析全文的高維度餘弦相似度檢索"
        },
        "explorer-tab": {
            title: "歷屆試題瀏覽器",
            desc: "依據考試年度、名稱及科目分層瀏覽，檢視原題重現與專家詳解"
        },
        "stats-tab": {
            title: "資料統計與系統介紹",
            desc: " AquaRAG 向量檢索系統架構、效能指標及收錄範圍統計"
        }
    };

    // 1. SPA ROUTING
    navButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            switchTab(targetTab);
        });
    });

    function switchTab(tabId) {
        state.activeTab = tabId;
        
        // Update menu buttons
        navButtons.forEach(b => {
            if (b.getAttribute("data-tab") === tabId) {
                b.classList.add("active");
            } else {
                b.classList.remove("active");
            }
        });

        // Update tab content displays
        tabContents.forEach(c => {
            if (c.id === tabId) {
                c.classList.add("active");
            } else {
                c.classList.remove("active");
            }
        });

        // Update header
        currentTabTitle.textContent = tabInfo[tabId].title;
        currentTabDesc.textContent = tabInfo[tabId].desc;
        
        // Lazy load tab data
        if (tabId === "stats-tab" && !state.stats) {
            loadStats();
        } else if (tabId === "explorer-tab" && state.examSets.length === 0) {
            loadExamSets();
        }
    }

    // 2. MARKDOWN PARSER (PURE JS)
    function parseMarkdown(md) {
        if (!md) return "";
        
        // Escape HTML to prevent injection, but preserve common tags we might want
        let html = md
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
        
        // Restore blockquotes since we escaped >
        // Replaces lines starting with &gt; with blockquotes
        html = html.replace(/^&gt;\s?(.*)$/gm, '<blockquote><p>$1</p></blockquote>');
        
        // Group adjacent blockquotes
        html = html.replace(/<\/blockquote>\n<blockquote>/g, '\n');
        
        // Headers
        html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
        html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
        html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
        
        // Bold
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Inline Code
        html = html.replace(/`(.*?)`/g, '<code>$1</code>');
        
        // Line-by-line parsing to extract markdown tables and format paragraphs
        const lines = html.split('\n');
        const processed = [];
        let inTable = false;
        let tableLines = [];
        
        for (let line of lines) {
            let trimmed = line.trim();
            
            // Check if line is a table row
            if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
                inTable = true;
                tableLines.push(trimmed);
                continue;
            } else if (inTable) {
                // Table ended, process tableLines
                processed.push(parseHTMLTable(tableLines));
                tableLines = [];
                inTable = false;
            }
            
            // Handle regular paragraphs vs headers/blockquotes
            if (trimmed.startsWith('<h1>') || trimmed.startsWith('<h2>') || trimmed.startsWith('<h3>') || 
                trimmed.startsWith('<blockquote>') || trimmed.startsWith('</blockquote') || !trimmed) {
                processed.push(line);
            } else {
                processed.push(`<p>${line}</p>`);
            }
        }
        
        // If file ends with a table
        if (inTable) {
            processed.push(parseHTMLTable(tableLines));
        }
        
        return processed.join('\n');
    }

    function parseHTMLTable(lines) {
        if (lines.length === 0) return "";
        let html = "<table>\n";
        let headersParsed = false;
        
        for (let line of lines) {
            // Extract cells split by pipe
            let cells = line.split('|').map(c => c.trim()).filter((c, i, arr) => i > 0 && i < arr.length - 1);
            
            // Skip divider rows like |---|---|
            if (cells.every(c => c.startsWith('-') || c.startsWith(' :') || c.endsWith(':'))) {
                continue;
            }
            
            html += "  <tr>\n";
            for (let cell of cells) {
                // Restore escaped line breaks inside cells
                let content = cell.replace(/&lt;br&gt;/g, '<br>');
                content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                
                if (!headersParsed) {
                    html += `    <th>${content}</th>\n`;
                } else {
                    html += `    <td>${content}</td>\n`;
                }
            }
            html += "  </tr>\n";
            if (!headersParsed && cells.length > 0) {
                headersParsed = true;
            }
        }
        html += "</table>";
        return html;
    }

    // 3. API OPERATIONS
    
    // Load statistics
    async function loadStats() {
        try {
            const res = await fetch("/api/stats");
            const data = await res.json();
            state.stats = data;
            
            statExamSets.textContent = data.exam_sets_count;
            statQuestions.textContent = data.questions_count;
            statDbSize.textContent = `${data.db_size_mb} MB`;
            
            if (data.active_model) {
                document.querySelector(".model-name").textContent = data.active_model;
            }
            if (data.active_desc) {
                document.querySelector(".model-desc").textContent = data.active_desc;
            }
        } catch (e) {
            console.error("Failed to load statistics:", e);
        }
    }

    // Load Exam sets for explorer
    async function loadExamSets() {
        try {
            const res = await fetch("/api/exam-sets");
            const data = await res.json();
            state.examSets = data;
            renderTree(data);
        } catch (e) {
            treeContainer.innerHTML = `<div class="tree-loading error"><i class="fa-solid fa-triangle-exclamation"></i> 載入失敗</div>`;
            console.error("Failed to load exam sets:", e);
        }
    }

    // Render explorer tree
    function renderTree(examSets, filterText = "") {
        treeContainer.innerHTML = "";
        
        const filteredSets = examSets.filter(set => {
            if (!filterText) return true;
            const query = filterText.toLowerCase();
            return set.exam_set.toLowerCase().includes(query) || 
                   set.questions.some(q => q.question_title.toLowerCase().includes(query) || q.question_num.toLowerCase().includes(query));
        });

        if (filteredSets.length === 0) {
            treeContainer.innerHTML = `<div class="tree-loading">無匹配的題目</div>`;
            return;
        }

        filteredSets.forEach(set => {
            const nodeDiv = document.createElement("div");
            nodeDiv.className = "tree-node";
            
            // Expand by default if filter is active
            if (filterText) {
                nodeDiv.classList.add("expanded");
            }

            const headerDiv = document.createElement("div");
            headerDiv.className = "tree-header";
            
            // Extract short title (strip "第 X 套試題：")
            const cleanSetName = set.exam_set.replace(/^第\s*\d+\s*套試題：/, "");
            headerDiv.innerHTML = `<i class="fa-solid fa-chevron-right"></i> <span title="${set.exam_set}">${cleanSetName}</span>`;
            
            const childrenDiv = document.createElement("div");
            childrenDiv.className = "tree-children";

            // Render children questions
            set.questions.forEach(q => {
                const leafDiv = document.createElement("div");
                leafDiv.className = "tree-leaf";
                if (state.activeQuestionId === q.id) {
                    leafDiv.classList.add("selected");
                }
                leafDiv.textContent = `${q.question_num}：${q.question_title}`;
                leafDiv.title = `${q.question_num}：${q.question_title}`;
                
                leafDiv.addEventListener("click", () => {
                    document.querySelectorAll(".tree-leaf").forEach(l => l.classList.remove("selected"));
                    leafDiv.classList.add("selected");
                    loadQuestionDetail(q.id);
                });
                
                childrenDiv.appendChild(leafDiv);
            });

            headerDiv.addEventListener("click", () => {
                nodeDiv.classList.toggle("expanded");
            });

            nodeDiv.appendChild(headerDiv);
            nodeDiv.appendChild(childrenDiv);
            treeContainer.appendChild(nodeDiv);
        });
    }

    // Filter tree in real time
    explorerFilter.addEventListener("input", (e) => {
        renderTree(state.examSets, e.target.value);
    });

    // Load question detail
    async function loadQuestionDetail(qid) {
        state.activeQuestionId = qid;
        contentPlaceholder.style.display = "none";
        questionDetailArticle.style.display = "none";
        
        // Show loading state
        contentPlaceholder.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i><h3>題目解析載入中...</h3>`;
        contentPlaceholder.style.display = "flex";

        try {
            const res = await fetch(`/api/question/${qid}`);
            const q = await res.json();
            
            contentPlaceholder.style.display = "none";
            questionDetailArticle.style.display = "block";
            
            // Update UI elements
            detailExamSet.textContent = q.exam_set;
            detailQTitle.textContent = q.question_title;
            detailQNum.textContent = q.question_num;
            detailContent.innerHTML = parseMarkdown(q.full_content);
            
            // Scroll detail pane to top
            document.querySelector(".explorer-content").scrollTop = 0;
        } catch (e) {
            contentPlaceholder.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i><h3>載入失敗</h3><p>請重新點擊題目或檢查伺服器狀態。</p>`;
            console.error("Failed to load question details:", e);
        }
    }

    // 4. SEMANTIC SEARCH
    
    // Top-K slider binding
    searchTopKRange.addEventListener("input", (e) => {
        topKValSpan.textContent = e.target.value;
    });

    async function executeSearch() {
        const query = searchQueryInput.value.trim();
        if (!query) return;

        searchResultsList.innerHTML = `<div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i><p>語意匹配中，請稍候...</p></div>`;
        searchResultsStats.style.display = "none";

        try {
            const topK = searchTopKRange.value;
            const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&top_k=${topK}`);
            const results = await res.json();

            searchResultsList.innerHTML = "";
            
            if (results.length === 0) {
                searchResultsList.innerHTML = `<div class="empty-state"><i class="fa-solid fa-magnifying-glass"></i><p>找不到符合條件的內容，請調整關鍵字</p></div>`;
                return;
            }

            resultsCountSpan.textContent = results.length;
            searchResultsStats.style.display = "block";

            results.forEach(r => {
                const card = document.createElement("div");
                card.className = "result-card";
                
                const matchPct = Math.round(r.score * 100);
                
                card.innerHTML = `
                    <div class="result-meta">
                        <span class="result-badge">${r.exam_set}</span>
                        <div class="result-score-container">
                            <div class="score-bar-bg">
                                <div class="score-bar-fill" style="width: ${matchPct}%"></div>
                            </div>
                            <span class="score-text">${matchPct}%</span>
                        </div>
                    </div>
                    <h3>${r.question_num}：${r.question_title}</h3>
                    <div class="result-preview">${r.original_question || r.full_content.substring(0, 150) + "..."}</div>
                `;
                
                card.addEventListener("click", () => {
                    openModal(r.exam_set, `${r.question_num}：${r.question_title}`, r.full_content);
                });
                
                searchResultsList.appendChild(card);
            });

        } catch (e) {
            searchResultsList.innerHTML = `<div class="empty-state error"><i class="fa-solid fa-triangle-exclamation"></i><p>搜尋失敗，請檢查 API 與伺服器連線。</p></div>`;
            console.error("Search failed:", e);
        }
    }

    searchSubmitBtn.addEventListener("click", executeSearch);
    searchQueryInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") executeSearch();
    });

    // 5. RAG CHAT
    
    // Auto-expand textarea
    chatInput.addEventListener("input", function() {
        this.style.height = "auto";
        this.style.height = (this.scrollHeight - 4) + "px";
    });

    // Submit question
    chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        submitChat();
    });

    let isComposingText = false;
    chatInput.addEventListener("compositionstart", () => {
        isComposingText = true;
    });
    chatInput.addEventListener("compositionend", () => {
        isComposingText = false;
    });

    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            if (isComposingText) {
                return;
            }
            if (!e.shiftKey) {
                e.preventDefault();
                submitChat();
            }
        }
    });

    // Suggestion chips binding
    suggestButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            chatInput.value = btn.textContent;
            submitChat();
        });
    });

    async function submitChat() {
        const message = chatInput.value.trim();
        if (!message) return;

        // Clear input box
        chatInput.value = "";
        chatInput.style.height = "auto";

        // Disable input during request
        chatInput.disabled = true;
        sendBtn.disabled = true;

        // Add user message to history
        appendMessage("user", message);
        
        // Add streaming model message placeholder
        const aiMsgDiv = appendMessage("assistant", "", true); // isStreaming = true
        
        // Hide references drawer if open
        citationsPanel.style.display = "none";

        try {
            const customApiKey = localStorage.getItem("aquarag_gemini_api_key") || "";
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    message: message,
                    history: state.chatHistory,
                    api_key: customApiKey
                })
            });

            if (!response.ok) {
                throw new Error("伺服器端錯誤，請確認本機 Ollama 服務是否正常啟動。");
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            
            let fullText = "";
            let buffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n\n");
                
                // Keep the last partial line in buffer
                buffer = lines.pop();

                for (const line of lines) {
                    if (!line.trim()) continue;
                    
                    // SSE parsing
                    const eventMatch = line.match(/^event:\s*(\w+)/m);
                    const dataMatch = line.match(/^data:\s*(.+)$/m);
                    
                    if (eventMatch && dataMatch) {
                        const event = eventMatch[1];
                        const dataStr = dataMatch[1];
                        
                        if (event === "citations") {
                            const citations = JSON.parse(dataStr);
                            state.currentCitations = citations;
                            renderCitations(citations);
                        } else if (event === "text") {
                            const dataObj = JSON.parse(dataStr);
                            const text = dataObj.text;
                            fullText += text;
                            aiMsgDiv.querySelector(".msg-content-text").innerHTML = parseMarkdown(fullText);
                            scrollToBottom();
                        } else if (event === "done") {
                            // Chat streaming done
                        } else if (event === "error") {
                            const errObj = JSON.parse(dataStr);
                            throw new Error(errObj.error);
                        }
                    }
                }
            }

            // Remove streaming class, finalize history
            aiMsgDiv.classList.remove("streaming");
            
            // Append citations chips to the AI bubble
            if (state.currentCitations.length > 0) {
                const chipsDiv = document.createElement("div");
                chipsDiv.className = "chat-citation-chips";
                chipsDiv.innerHTML = `<span class="citation-label"><i class="fa-solid fa-book-bookmark"></i> 檢索考題來源：</span>`;
                
                state.currentCitations.forEach((cit, idx) => {
                    const chip = document.createElement("button");
                    chip.className = "citation-chip";
                    const cleanSet = cit.exam_set.replace(/^第\s*\d+\s*套試題：/, "").substring(0, 10) + "...";
                    chip.innerHTML = `[${idx+1}] ${cleanSet} ${cit.question_num}`;
                    chip.title = `${cit.exam_set} - ${cit.question_num}`;
                    
                    chip.addEventListener("click", () => {
                        // Open reference in modal
                        openModalFromId(cit.id);
                    });
                    
                    chipsDiv.appendChild(chip);
                });
                aiMsgDiv.querySelector(".msg-content").appendChild(chipsDiv);
            }

            // Save conversation history
            state.chatHistory.push({ role: "user", content: message });
            state.chatHistory.push({ role: "assistant", content: fullText });
            
            // Scroll to bottom
            scrollToBottom();

        } catch (e) {
            console.error("Chat streaming error:", e);
            aiMsgDiv.classList.remove("streaming");
            aiMsgDiv.querySelector(".msg-content-text").innerHTML = `<p style="color: var(--accent-orange)"><i class="fa-solid fa-circle-exclamation"></i> <strong>錯誤：</strong>${e.message || "連線至 Ollama 失敗，請確認 Qwen-2.5 模型是否就緒。"}</p>`;
        } finally {
            chatInput.disabled = false;
            sendBtn.disabled = false;
            chatInput.focus();
        }
    }

    // Helper to render citations panel
    function renderCitations(citations) {
        citationsList.innerHTML = "";
        citationsPanel.style.display = "flex";

        citations.forEach((cit, index) => {
            const card = document.createElement("div");
            card.className = "citation-card";
            
            const matchPct = Math.round(cit.score * 100);
            
            card.innerHTML = `
                <div class="cit-meta">
                    <span>來源 [${index+1}]：${cit.question_num}</span>
                    <span class="cit-score">匹配度: ${matchPct}%</span>
                </div>
                <div class="cit-title">${cit.question_title}</div>
                <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">${cit.exam_set}</div>
            `;
            
            card.addEventListener("click", () => {
                openModalFromId(cit.id);
            });
            
            citationsList.appendChild(card);
        });
    }

    closeCitationsBtn.addEventListener("click", () => {
        citationsPanel.style.display = "none";
    });

    // Helper to append messages to history UI
    function appendMessage(role, text, isStreaming = false) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${role === "user" ? "user-msg" : "system-msg"}`;
        
        let avatarIcon = '<i class="fa-solid fa-robot"></i>';
        if (role === "user") avatarIcon = '<i class="fa-solid fa-user"></i>';
        
        msgDiv.innerHTML = `
            <div class="msg-avatar">${avatarIcon}</div>
            <div class="msg-content">
                <div class="msg-content-text">${isStreaming ? '<span class="typing-indicator"><span></span><span></span><span></span></span>' : parseMarkdown(text)}</div>
            </div>
        `;
        
        if (isStreaming) {
            msgDiv.classList.add("streaming");
        }
        
        chatHistoryDiv.appendChild(msgDiv);
        scrollToBottom();
        return msgDiv;
    }

    function scrollToBottom() {
        chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight;
    }

    // 6. MODAL SYSTEM
    function openModal(examSet, title, content) {
        modalExamSet.textContent = examSet;
        modalTitle.textContent = title;
        modalContent.innerHTML = parseMarkdown(content);
        
        citationModal.classList.add("active");
    }

    async function openModalFromId(qid) {
        try {
            const res = await fetch(`/api/question/${qid}`);
            const q = await res.json();
            openModal(q.exam_set, `${q.question_num}：${q.question_title}`, q.full_content);
        } catch (e) {
            console.error("Failed to load question details for modal:", e);
        }
    }

    function closeModal() {
        citationModal.classList.remove("active");
    }

    modalCloseBtn.addEventListener("click", closeModal);
    citationModal.addEventListener("click", (e) => {
        if (e.target === citationModal) closeModal();
    });

    // Esc key closes modal
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            closeModal();
            if (settingsModal) settingsModal.classList.remove("active");
            citationsPanel.style.display = "none";
        }
    });

    // 7. SETTINGS EVENT LISTENERS
    if (settingsToggleBtn) {
        settingsToggleBtn.addEventListener("click", () => {
            const savedKey = localStorage.getItem("aquarag_gemini_api_key") || "";
            userGeminiKeyInput.value = savedKey;
            settingsModal.classList.add("active");
        });
    }

    if (settingsCloseBtn) {
        settingsCloseBtn.addEventListener("click", () => {
            settingsModal.classList.remove("active");
        });
    }

    if (settingsModal) {
        settingsModal.addEventListener("click", (e) => {
            if (e.target === settingsModal) {
                settingsModal.classList.remove("active");
            }
        });
    }

    if (toggleKeyVisibilityBtn) {
        toggleKeyVisibilityBtn.addEventListener("click", () => {
            const icon = toggleKeyVisibilityBtn.querySelector("i");
            if (userGeminiKeyInput.type === "password") {
                userGeminiKeyInput.type = "text";
                icon.classList.remove("fa-eye");
                icon.classList.add("fa-eye-slash");
            } else {
                userGeminiKeyInput.type = "password";
                icon.classList.remove("fa-eye-slash");
                icon.classList.add("fa-eye");
            }
        });
    }

    if (settingsSaveBtn) {
        settingsSaveBtn.addEventListener("click", () => {
            const key = userGeminiKeyInput.value.trim();
            if (key) {
                localStorage.setItem("aquarag_gemini_api_key", key);
                alert("Gemini API Key 已儲存至本地瀏覽器！");
            } else {
                localStorage.removeItem("aquarag_gemini_api_key");
                alert("自訂金鑰已清除，將使用系統預設金鑰！");
            }
            settingsModal.classList.remove("active");
            loadStats();
        });
    }

    if (settingsClearBtn) {
        settingsClearBtn.addEventListener("click", () => {
            localStorage.removeItem("aquarag_gemini_api_key");
            userGeminiKeyInput.value = "";
            alert("自訂金鑰已清除，將使用系統預設金鑰！");
            settingsModal.classList.remove("active");
            loadStats();
        });
    }

    // Start with chat tab active
    switchTab("chat-tab");
    loadStats(); // Load stats on startup to set the active model badge
});

class InterceptResult:
    def __init__(self, status, feedback=""):
        self.status = status
        self.feedback = feedback

class HubInterceptor:
    def __init__(self, active_peers, max_rounds=3, collab_rate=10):
        self.active_peers = active_peers
        self.max_rounds = max_rounds
        self.collab_rate = collab_rate

    def broadcast_for_review(self, primary_peer, action):
        """
        In a real system, this broadcasts the draft action to all other peers via IPC 
        and waits for their votes. Overridden in tests.
        """
        return [] # Default empty for N=1

    def evaluate_action(self, primary_peer, action, round_num=1):
        # 1. Read-only bypass
        if hasattr(action, 'is_read_only') and action.is_read_only():
            return InterceptResult("APPROVED")
            
        N = len(self.active_peers)
        
        # 2. N=1 Logic (Isolation)
        if N == 1:
            return InterceptResult("ESCALATE_TO_USER", "N=1 Isolation: Fallback to HITL for Write Actions")
            
        # 3. Max Rounds Check
        if round_num >= self.max_rounds:
            return InterceptResult("ESCALATE_TO_USER")
            
        # 4. Broadcast for review
        review_results = self.broadcast_for_review(primary_peer, action)
        
        approvals = 1 # Primary always implicitly approves their own action
        rejections = 0
        abstains = 0
        feedbacks = []
        
        for result in review_results:
            if result.vote == "AGREE":
                approvals += 1
            elif result.vote == "DISAGREE":
                rejections += 1
                feedbacks.append(result.reason)
            else: # ABSTAIN or Timeout
                abstains += 1
                
        # 5. Collab Rate Dependent Evaluation
        if self.collab_rate == 10:
            # Unanimity required. Approvals must equal N.
            if approvals == N:
                return InterceptResult("APPROVED")
            elif abstains > 0:
                # If there are abstains/timeouts, unanimity is impossible. Must fail to human.
                return InterceptResult("ESCALATE_TO_USER", "Unanimity required but Abstain/Timeout occurred (INV-03).")
            else:
                feedback_str = " | ".join(feedbacks)
                return InterceptResult("REJECTED_WITH_FEEDBACK", feedback_str)
        else:
            # Quorum required
            quorum = (N // 2) + 1
            if approvals >= quorum:
                return InterceptResult("APPROVED")
            else:
                feedback_str = " | ".join(feedbacks) if feedbacks else "Quorum not met (Timeouts/Abstentions)"
                return InterceptResult("REJECTED_WITH_FEEDBACK", feedback_str)

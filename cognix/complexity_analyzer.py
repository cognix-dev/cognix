# cognix/complexity_analyzer.py - 新規ファイル作成

class GoalComplexityAnalyzer:
    """ゴールの複雑性を自動判定"""
    
    def __init__(self):
        # 複雑性レベルの定義
        self.simple_patterns = {
            'keywords': ['hello', 'calculator', 'converter', 'timer', 'counter', 'display', 'print', 'show'],
            'phrases': ['hello world', 'simple', 'basic', 'easy', 'quick'],
            'operations': ['add', 'subtract', 'multiply', 'divide', 'convert', 'format']
        }
        
        self.complex_patterns = {
            'keywords': ['system', 'application', 'database', 'api', 'server', 'authentication', 'framework'],
            'phrases': ['full stack', 'enterprise', 'production ready', 'scalable', 'distributed'],
            'operations': ['integrate', 'deploy', 'scale', 'optimize', 'secure', 'monitor']
        }
        
        self.medium_indicators = {
            'keywords': ['app', 'tool', 'utility', 'manager', 'client', 'interface'],
            'phrases': ['with gui', 'file processing', 'data analysis'],
            'operations': ['process', 'manage', 'analyze', 'generate', 'parse']
        }
    
    def analyze_complexity(self, goal: str) -> dict:
        """ゴールの複雑性を分析"""
        goal_lower = goal.lower()
        
        # スコア計算
        simple_score = self._calculate_score(goal_lower, self.simple_patterns)
        medium_score = self._calculate_score(goal_lower, self.medium_indicators)
        complex_score = self._calculate_score(goal_lower, self.complex_patterns)
        
        # 長さによる調整
        length_factor = len(goal.split())
        if length_factor <= 3:
            simple_score += 2
        elif length_factor >= 8:
            complex_score += 2
        
        # 判定
        max_score = max(simple_score, medium_score, complex_score)
        
        if simple_score == max_score and simple_score > 0:
            complexity = "simple"
        elif complex_score == max_score and complex_score > 1:
            complexity = "complex"
        else:
            complexity = "medium"
        
        return {
            "complexity": complexity,
            "confidence": max_score / 5.0,  # 0-1のスコア
            "scores": {
                "simple": simple_score,
                "medium": medium_score,
                "complex": complex_score
            },
            "reasoning": self._generate_reasoning(goal, complexity, max_score)
        }
    
    def _calculate_score(self, goal: str, patterns: dict) -> int:
        """パターンマッチングによるスコア計算"""
        score = 0
        
        for keyword in patterns['keywords']:
            if keyword in goal:
                score += 2
        
        for phrase in patterns['phrases']:
            if phrase in goal:
                score += 3
        
        for operation in patterns['operations']:
            if operation in goal:
                score += 1
        
        return score
    
    def _generate_reasoning(self, goal: str, complexity: str, score: int) -> str:
        """判定理由の生成"""
        reasons = []
        
        if complexity == "simple":
            reasons.append("Contains basic operation keywords")
            reasons.append("Short and focused scope")
        elif complexity == "complex":
            reasons.append("System-level or enterprise keywords detected")
            reasons.append("Multiple components implied")
        else:
            reasons.append("Mid-level application complexity")
            reasons.append("Moderate scope and features")
        
        return f"Classified as {complexity} (confidence: {score}/5). " + "; ".join(reasons)

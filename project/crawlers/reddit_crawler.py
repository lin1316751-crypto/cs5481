"""
Reddit 爬虫模块
抓取财经相关子版块的帖子和评论
"""
import time
import praw
import prawcore
from datetime import datetime
from typing import List, Dict, Any
from utils.logger import setup_logger
from utils.redis_client import RedisClient

logger = setup_logger('reddit_crawler')


class RedditCrawler:
    """Reddit 爬虫类"""
    
    def __init__(self, config: dict, redis_client: RedisClient):
        """
        初始化 Reddit 爬虫
        
        Args:
            config: Reddit 配置字典
            redis_client: Redis 客户端实例
        """
        self.config = config
        self.redis_client = redis_client
        
        try:
            self.reddit = praw.Reddit(
                client_id=config['client_id'],
                client_secret=config['client_secret'],
                user_agent=config['user_agent']
            )
            logger.info("Reddit API 初始化成功")
        except Exception as e:
            logger.error(f"Reddit API 初始化失败: {e}")
            raise
        
        self.subreddits = config.get('subreddits', ['investing', 'finance'])
        self.posts_limit = config.get('posts_limit', 50)
        self.comments_limit = config.get('comments_limit', 30)
    
    def crawl(self) -> Dict[str, int]:
        """
        执行抓取任务
        
        Returns:
            dict: 抓取统计信息 {'posts': 数量, 'comments': 数量, 'errors': 数量}
        """
        stats = {'posts': 0, 'comments': 0, 'errors': 0}
        
        logger.info("开始抓取 Reddit 数据...")
        
        for subreddit_name in self.subreddits:
            sub_posts = 0
            sub_comments = 0
            
            try:
                logger.info(f"正在抓取子版块: r/{subreddit_name}")
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # 抓取新帖子
                post_index = 0
                for submission in subreddit.new(limit=self.posts_limit):
                    post_index += 1
                    
                    # 显示正在处理的帖子
                    logger.info(f"  [{post_index}/{self.posts_limit}] 抓取帖子: {submission.title[:60]}...")
                    
                    # 提取帖子信息
                    post_data = self._extract_post_data(submission, subreddit_name)
                    if post_data and self.redis_client.push_data(post_data):
                        stats['posts'] += 1
                        sub_posts += 1
                        logger.debug(f"    ✓ 帖子已保存 (ID: {submission.id})")
                    
                    # 抓取评论
                    logger.info(f"    → 正在抓取评论 (目标: {self.comments_limit} 条)...")
                    comments_count = self._crawl_comments(submission, subreddit_name)
                    stats['comments'] += comments_count
                    sub_comments += comments_count
                    logger.info(f"    ✓ 评论抓取完成: {comments_count} 条")
                    
                    # 避免请求过快
                    time.sleep(0.5)
                
                logger.info(
                    f"✓ 子版块 r/{subreddit_name} 抓取完成 - "
                    f"帖子: {sub_posts}, 评论: {sub_comments}"
                )
                
            except prawcore.ResponseException as e:
                # 修复:使用 ResponseException 替代 RateLimitExceeded
                if e.response.status_code == 429:
                    logger.warning(f"Reddit API 速率限制: {e}, 等待后重试...")
                    time.sleep(60)  # 等待1分钟
                else:
                    logger.error(f"Reddit API 响应错误 ({e.response.status_code}): {e}")
                stats['errors'] += 1
                
            except Exception as e:
                logger.error(f"抓取子版块 r/{subreddit_name} 时出错: {e}")
                stats['errors'] += 1
        
        logger.info(f"Reddit 抓取完成 - 帖子: {stats['posts']}, 评论: {stats['comments']}, 错误: {stats['errors']}")
        return stats
    
    def _extract_post_data(self, submission, subreddit_name: str) -> Dict[str, Any]:
        """
        提取帖子数据 - 尽可能完整的信息
        
        Args:
            submission: PRAW submission 对象
            subreddit_name: 子版块名称
        
        Returns:
            dict: 帖子数据
        """
        try:
            # 组合标题和正文
            text = submission.title
            if submission.selftext:
                text += "\n\n" + submission.selftext
            
            data = {
                # 基础字段
                'text': text,
                'source': 'reddit_post',
                'timestamp': int(submission.created_utc),
                'url': f"https://www.reddit.com{submission.permalink}",
                
                # Reddit 特有字段
                'subreddit': subreddit_name,
                'post_id': submission.id,
                'author': str(submission.author) if submission.author else '[deleted]',
                
                # 互动数据（用于趋势分析）
                'score': submission.score,
                'upvote_ratio': getattr(submission, 'upvote_ratio', 0),
                'num_comments': submission.num_comments,
                
                # 内容类型
                'is_self': submission.is_self,
                'is_video': submission.is_video,
                'link_flair_text': submission.link_flair_text,
                
                # 其他元数据
                'gilded': submission.gilded,
                'distinguished': submission.distinguished,
                'stickied': submission.stickied,
                'over_18': submission.over_18,
                'spoiler': submission.spoiler,
                
                # 标题单独保留（用于关键词提取）
                'title': submission.title,
                'selftext': submission.selftext if submission.selftext else ''
            }
            return data
        except Exception as e:
            logger.error(f"提取帖子数据失败: {e}")
            return None
    
    def _crawl_comments(self, submission, subreddit_name: str) -> int:
        """
        抓取帖子的评论
        
        Args:
            submission: PRAW submission 对象
            subreddit_name: 子版块名称
        
        Returns:
            int: 成功抓取的评论数量
        """
        count = 0
        try:
            # 展开所有评论（限制数量以避免过多请求）
            logger.debug(f"      → 展开评论树...")
            submission.comments.replace_more(limit=0)
            
            # 获取评论列表
            all_comments = submission.comments.list()
            logger.debug(f"      → 找到 {len(all_comments)} 条评论,排序中...")
            
            # 按评分排序，取前N条
            sorted_comments = sorted(
                all_comments, 
                key=lambda c: c.score if hasattr(c, 'score') else 0, 
                reverse=True
            )[:self.comments_limit]
            
            logger.debug(f"      → 准备保存前 {len(sorted_comments)} 条评论")
            
            for idx, comment in enumerate(sorted_comments, 1):
                try:
                    comment_data = self._extract_comment_data(comment, subreddit_name)
                    if comment_data and self.redis_client.push_data(comment_data):
                        count += 1
                        logger.debug(f"        ✓ [{idx}/{len(sorted_comments)}] 评论已保存")
                except Exception as e:
                    logger.warning(f"        ✗ [{idx}/{len(sorted_comments)}] 保存评论失败: {e}")
            
        except prawcore.ResponseException as e:
            logger.error(
                f"      ✗ Reddit API 错误 (帖子: {submission.id}): "
                f"{e.response.status_code} - {e.response.reason}"
            )
        except Exception as e:
            logger.error(
                f"      ✗ 抓取评论时出错 (帖子: {submission.id}, "
                f"标题: {submission.title[:40]}...): {e}"
            )
        
        return count
    
    def _extract_comment_data(self, comment, subreddit_name: str) -> Dict[str, Any]:
        """
        提取评论数据 - 完整信息（用于情感分析）
        
        Args:
            comment: PRAW comment 对象
            subreddit_name: 子版块名称
        
        Returns:
            dict: 评论数据
        """
        try:
            data = {
                # 基础字段
                'text': comment.body,
                'source': 'reddit_comment',
                'timestamp': int(comment.created_utc),
                'url': f"https://www.reddit.com{comment.permalink}",
                
                # Reddit 特有字段
                'subreddit': subreddit_name,
                'comment_id': comment.id,
                'author': str(comment.author) if comment.author else '[deleted]',
                
                # 互动数据（用于情感分析权重）
                'score': comment.score,
                'gilded': comment.gilded,
                'distinguished': comment.distinguished,
                'stickied': comment.stickied,
                
                # 评论上下文
                'is_submitter': comment.is_submitter,  # 是否是帖子作者
                'parent_id': comment.parent_id,
                'link_id': comment.link_id
            }
            return data
        except Exception as e:
            logger.error(f"提取评论数据失败: {e}")
            return None


def main():
    """测试函数"""
    import yaml
    
    # 加载配置
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 初始化 Redis 客户端
    redis_client = RedisClient(**config['redis'])
    
    # 初始化并运行爬虫
    crawler = RedditCrawler(config['reddit'], redis_client)
    stats = crawler.crawl()
    
    print(f"抓取完成: {stats}")
    
    # 关闭连接
    redis_client.close()


if __name__ == '__main__':
    main()

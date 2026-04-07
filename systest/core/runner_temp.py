    def _resolve_test_dir(self):
        """确定测试目录：用户指定 > 自动检测结果（已更新到 runtime_config）

        现在环境检测和配置更新已经在 __init__ 开头完成了,
        这里只需要处理用户手动覆盖和最后的创建验证
        """
        # 1) 用户手动指定（最高优先级）
        if self.test_dir_override:
            self.test_dir = Path(self.test_dir_override).absolute()
            if not self.test_dir.exists():
                self.test_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ 测试目录：{self.test_dir} (手动指定)")
            return

        # 2) 从自动检测结果读取（已经更新到 runtime_config）
        if self.runtime_config.get('test_dir'):
            config_test_dir = self.runtime_config['test_dir']
            self.test_dir = Path(config_test_dir).absolute()
            try:
                if not self.test_dir.exists():
                    self.test_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"✅ 测试目录：{self.test_dir} (自动检测)")
            except Exception as e:
                logger.warning(f"⚠️  无法创建测试目录：{self.test_dir} ({e})")
                # 多级回退：先试开发板默认
                try:
                    self.test_dir = Path('/mapdata/ufs_test').absolute()
                    if not self.test_dir.exists():
                        self.test_dir.mkdir(parents=True, exist_ok=True)
                    logger.warning(f"⚠️  回退到开发板默认：{self.test_dir}")
                except Exception:
                    # 最后回退到 /tmp
                    self.test_dir = Path('/tmp/ufs_test').absolute()
                    if not self.test_dir.exists():
                        self.test_dir.mkdir(parents=True, exist_ok=True)
                    logger.warning(f"⚠️  回退到临时目录：{self.test_dir}")
            return

        # 3) 极端情况：自动检测也没给出结果，回退默认
        self.test_dir = Path('/mapdata/ufs_test').absolute()
        try:
            if not self.test_dir.exists():
                self.test_dir.mkdir(parents=True, exist_ok=True)
            logger.warning(f"⚠️  自动检测失败，使用开发板默认：{self.test_dir}")
        except Exception:
            # 最后回退到 /tmp
            self.test_dir = Path('/tmp/ufs_test').absolute()
            if not self.test_dir.exists():
                self.test_dir.mkdir(parents=True, exist_ok=True)
            logger.warning(f"⚠️  回退到临时目录：{self.test_dir}")

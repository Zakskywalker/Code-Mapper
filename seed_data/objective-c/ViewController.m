@interface ViewController : NSObject
@property(nonatomic, strong) NSString *name;
- (NSString *)title;
@end

@implementation ViewController
- (NSString *)title { return @"seed"; }
@end
